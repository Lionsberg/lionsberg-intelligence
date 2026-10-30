// bodies-talk.js: the Bodies room's line to a terminal body (DESIGN-BODIES §13).
//
// A terminal body (the prime, a background body, another window) lives in its own window. When
// this computer's server can reach its conversation, the room shows it and speaks into it; when
// it cannot, the room says so plainly and never pretends a conversation exists.
//
// The interface (serve.py, written beside this view; until its routes exist every body reads as
// unreachable, so the room works today):
//   GET  /bodies/talk?body=<name>&since=<n>   server-sent events (`event: line`) of that body's
//                                             conversation, each {n, ts, kind: user|agent|tool|state,
//                                             text, turn}; a body it cannot read answers JSON
//                                             {refused} or {reachable: false, why} (404 or 409)
//   GET  /bodies/reach?body=<name>            {reachable, window, status, why}: whether words can be
//                                             sent to it from here (reading and sending differ)
//   POST /bodies/talk {body, text, confirmed: true}    the person's own words, from their own tap
//   POST /bodies/window {body, confirmed: true}        bring that body's window to the front here
// `body` is the name the live block gives: "prime", a background body's name, "window" for
// another window (several windows answer as one name, and the server says so).
//
// Everything a body sends is data: the room sets it as text, never as markup. No sound.

import { store, ON_PHONE } from "./state.js";

let TOKEN = null;
async function token() {
  if (TOKEN || store.source !== "server" || ON_PHONE) return TOKEN;
  try { const r = await fetch("/token", { cache: "no-store" }); if (r.ok) TOKEN = (await r.json()).token || null; } catch { /* no server */ }
  return TOKEN;
}
async function authed(url, init = {}) {
  const tk = await token();
  let dev = null;
  if (ON_PHONE) { try { dev = JSON.parse(localStorage.getItem("hud.device") || "null"); } catch { dev = null; } }
  return fetch(url, { ...init, headers: { ...(init.headers || {}), ...(tk ? { "X-HUD-Token": tk } : {}),
    ...(dev && dev.token ? { "X-HUD-Device": dev.token } : {}) } });
}
async function post(url, body) {
  if (store.source !== "server") return { ok: false, out: { reachable: false, why: "no-server" } };
  try {
    const r = await authed(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const out = await r.json().catch(() => ({}));
    return { ok: r.ok && out.reachable !== false && !out.refused, status: r.status, out };
  } catch { return { ok: false, status: 0, out: {} }; }
}

/**
 * talkTo(body, {onLine(line), onReach({reachable, why}), onCaughtUp(next)?, since?}) -> {send(text), close()}
 * `since` resumes from a transcript line already received (the room keeps what it drew across a
 * leave and return); onCaughtUp is called when the server has sent all it holds for now.
 * onReach is called once the server has answered (and again if that changes); onLine for every
 * line in order, from the first. A route that does not exist yet (404 or 405) reads as unreachable
 * and is not asked again until the body is chosen again.
 */
export function talkTo(body, { onLine, onReach, onCaughtUp = null, since = 0 }) {
  let stopped = false, ctrl = null, n = Math.max(0, since | 0), reach = null;
  const said = (r) => { if (stopped) return; if (!reach || reach.reachable !== r.reachable || reach.why !== r.why) { reach = r; try { onReach(r); } catch (e) { console.error(e); } } };
  const run = async () => {
    if (store.source !== "server") { said({ reachable: false, why: "no-server" }); return; }
    while (!stopped) {
      ctrl = new AbortController();
      try {
        const r = await authed(`/bodies/talk?body=${encodeURIComponent(body)}&since=${n}`, { cache: "no-store", signal: ctrl.signal });
        const type = r.headers.get("Content-Type") || "";
        if (!type.includes("event-stream")) {
          // a refusal in words, or a route this server does not have yet (404 or 405 with no words)
          const out = await r.json().catch(() => ({}));
          said({ reachable: false, why: out.why || out.refused || "not-yet" });
          return;
        }
        if (!r.body) throw new Error("no body");
        said({ reachable: true });
        const reader = r.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          let i;
          while ((i = buf.indexOf("\n\n")) >= 0) {
            const block = buf.slice(0, i); buf = buf.slice(i + 2);
            let data = "", ev = "";
            for (const line of block.split("\n")) { if (line.startsWith("data:")) data += line.slice(5).trim(); else if (line.startsWith("event:")) ev = line.slice(6).trim(); }
            if (!data) continue;
            let obj = null; try { obj = JSON.parse(data); } catch { continue; }
            if (ev === "caught_up") { if (obj && typeof obj.next === "number") n = Math.max(n, obj.next); if (onCaughtUp) { try { onCaughtUp(obj && obj.next); } catch (e) { console.error(e); } } continue; }
            if (obj && obj.reachable === false) { said({ reachable: false, why: obj.why || "" }); continue; }
            if (!obj || typeof obj.n !== "number" || obj.n < n) continue;
            n = obj.n + 1;
            try { onLine(obj); } catch (e) { console.error(e); }
          }
        }
      } catch { if (stopped) return; }
      if (stopped) return;
      await new Promise((res) => setTimeout(res, 3000));
    }
  };
  run();
  return {
    /** the person's own words, from their own tap: {ok, reason} */
    async send(text) {
      const r = await post("/bodies/talk", { body, text, confirmed: true });
      return { ok: r.ok, reason: (r.out && (r.out.refused || (r.out.reachable === false && r.out.why))) || null };
    },
    close() { stopped = true; if (ctrl) ctrl.abort(); },
  };
}

/** reach(body) -> {reachable, window, status, why}: whether words can be sent to it from here. */
export async function reach(body) {
  if (store.source !== "server") return { reachable: false, why: "no-server" };
  try {
    const r = await authed(`/bodies/reach?body=${encodeURIComponent(body)}`, { cache: "no-store" });
    const out = await r.json().catch(() => ({}));
    return { reachable: !!out.reachable, window: !!out.window, status: out.status || null, why: out.why || out.refused || null };
  } catch { return { reachable: false, why: null }; }
}

/** openWindow(body) -> {ok, refused}: bring that body's own window to the front, on the person's tap. */
export async function openWindow(body) {
  const r = await post("/bodies/window", { body, confirmed: true });
  return { ok: r.ok, refused: r.ok ? null : ((r.out && (r.out.refused || r.out.why)) || null), status: r.status };
}

/** handoffText(body) -> {ok, text, bytes, cut, card, review_min, why}: the text of a body's handoff,
    read through GET /bodies/handoff (only a body that keeps its own folder; never through a link).
    The text is data: the room sets it as text in Plain, never as markup. */
export async function handoffText(body) {
  if (store.source !== "server") return { ok: false, why: null };
  try {
    const r = await authed(`/bodies/handoff?body=${encodeURIComponent(body)}`, { cache: "no-store" });
    const out = await r.json().catch(() => ({}));
    if (!r.ok) return { ok: false, why: out.refused || null };
    return { ok: true, text: String(out.text || ""), bytes: out.bytes, cut: !!out.cut, card: out.card || null, folder: out.folder || null, review_min: out.review_min ?? null };
  } catch { return { ok: false, why: null }; }
}
