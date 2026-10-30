// dock-card.js: the context card around your agent's ask (DESIGN-DOCK §2.4).
//
// When your agent asks before it acts, the ask arrives here as one card, in the agent's own voice:
// the question as it would put it ("May I put this in your record: ...?"),
// made from what it would do; its own reason, else what it said just before, else its own
// description of the act; what would be written or sent, in plain type; where it reaches, in one
// line; the harness's title and exactly what would happen, folded. No and Yes, the biggest
// things on the card, where the thumb is; small and quiet above them: Explain first, Put it in
// my Deal, Yes for this kind (never for anything that leaves the computer). An ask left fifteen
// minutes goes into The Deal on its own (the host keeps that clock, so a closed tab still
// keeps it).
//
// Its face is in words only (never raw commands or step names such as "Newest
// session logs by mtime"). The question says what the act is for; under it, the
// agent's own reason or what it said just before; the harness's step name, its title and its raw
// input sit behind one fold, "The exact step". The host shows one ask at a time.
//
// Everything the agent sent is data: set as text, never as markup; no address is followed.

import { actFor } from "./deal.js";

/** renderAsk(ctx, ask, {onAnswer(answer) -> Promise<{ok, reason}>, foreign}) -> Element. `foreign`: the ask
    is another agent's (a worker's): only its own reason is shown, never words said in her conversation. */
export function renderAsk(ctx, ask, { onAnswer, foreign = false }) {
  if (ask && ask.kind === "worker") return renderWorkerAsk(ctx, ask, { onAnswer });
  if (ask && ask.kind === "act") return renderActAsk(ctx, ask, { onAnswer });
  if (ask && ask.kind === "keep") return renderKeepAsk(ctx, ask, { onAnswer });
  const { h } = ctx.card;
  const t = ctx.t;
  const card = h("article", { class: "card card--compact dock-ask", role: "group", "aria-label": t("dock.ask_label") });

  // the question, in the agent's own voice, made from what it would do; the harness's own title stays in the fold
  const q = question(ctx, ask);
  card.append(h("div", { class: "dock-ask-head" },
    h("h3", { class: "card-title dock-ask-q" }, q)));
  if (ask.untrusted) card.append(h("p", { class: "dock-untrusted" }, t("dock.from_something_read_line")));

  // its own words: its reason when it gave one, else what it said just before. The harness's own
  // description of the step is a step name, never words for the person: it stays in the fold.
  let described = null;
  try { const v = ask.input ? JSON.parse(ask.input) : null; described = v && typeof v.description === "string" ? v.description.trim() : null; } catch { /* not an object */ }
  const why = foreign ? ask.why : ask.why || ask.said;
  if (why) card.append(h("p", { class: "dock-ask-why" }, why));

  // what would be written or sent, in plain type, so it is read without opening the fold
  const seen = typeof ask.preview === "string" && ask.preview.trim() ? plainLines(ask.preview).split("\n").slice(0, 6).join("\n") : preview(ask);
  if (seen && !q.includes(seen)) card.append(h("blockquote", { class: "dock-preview" }, seen));

  // where it reaches: always said, in one line; in full ink when it leaves
  card.append(ask.leaves
    ? h("p", { class: "dock-reach dock-reach--leaves" }, t("dock.leaves_computer"))
    : h("p", { class: "dock-reach" }, t("dock.stays_on_computer")));

  const said = h("p", { class: "dust", role: "status" });
  const kinds = new Set((ask.options || []).map((o) => o.kind));
  const all = [];
  const answer = async (key) => {
    for (const x of all) x.disabled = true;
    const r = await onAnswer(key);
    if (!r || !r.ok) {
      said.textContent = (r && r.reason) || t("dock.answer_failed");
      for (const x of all) x.disabled = false;
    }
  };
  const btn = (key, label, cls) => { const b = h("button", { class: cls, type: "button" }, label); b.addEventListener("click", () => answer(key)); all.push(b); return b; };

  // the quiet ways, small, above the two answers
  const quiet = h("p", { class: "dock-ask-quiet" }, btn("explain", t("dock.answer.explain"), "link-btn"), btn("postpone", t("dock.answer.postpone"), "link-btn"));
  // a worker's ask: no "later" and no "yes for this kind"; its own name is on its face
  if (ask.from_worker) quiet.querySelector("button:nth-child(2)").remove();
  if (!ask.leaves && !ask.from_worker && kinds.has("allow_always")) {
    const k = btn("yes_kind", t("dock.answer.yes_kind"), "link-btn");
    k.setAttribute("title", t("dock.answer.yes_kind_scope", { kind: kindWords(ctx, ask.kind) }));
    quiet.append(k);
  }
  // the exact step: folded behind one link; the step's name, its title, its raw input; monospace only inside
  // the host's own sentence for the step, when it gives one, is all that is behind the fold
  const stepWords = ask.step != null ? plainStep(ask.step) : null;
  if (stepWords != null) {
    if (stepWords) card.append(h("details", { class: "dock-fold" }, h("summary", { class: "dust" }, t("dock.ask_exactly")), h("p", { class: "dust" }, stepWords)));
  } else if (whatWouldHappen(ask).length || ask.title || described) {
    const detail = whatWouldHappen(ask);
    card.append(h("details", { class: "dock-fold" }, h("summary", { class: "dust" }, t("dock.ask_exactly")),
      described ? h("p", { class: "dust" }, noPaths(described)) : null,
      ask.title && ask.title !== described ? h("p", { class: "dust" }, noPaths(ask.title)) : null, ...detail));
  }
  // No and Yes where the thumb is: the biggest things on the card, Yes nearest the right thumb
  const row = h("div", { class: "dock-answers" }, btn("not_this", t("dock.answer.no"), "pill dock-no"), btn("yes", t("dock.answer.yes"), "pill primary dock-yes"));
  card.append(quiet, row, said);
  return card;
}

/** The ask as the agent would put it to the person. */
export function question(ctx, ask) {
  const t = ctx.t;
  // the host's own words for the ask are its face, for every kind ("May I remember that …?", "Vega would like to …")
  if (ask && typeof ask.question === "string" && ask.question.trim()) return ask.question.trim();
  let v = null;
  try { v = ask.input ? JSON.parse(ask.input) : null; } catch { v = null; }
  const o = v && typeof v === "object" ? v : {};
  const cmd = String(o.command || "");
  // the kit's own record script: a card, a commitment, a line in the record
  const rec = cmd.match(/record\.py\s+append\b/) && cmd.match(/--body\s+'(\{[^']*\})'/);
  if (rec) {
    let title = null;
    try { const b = JSON.parse(rec[1]); title = b.title || b.text || null; } catch { /* not readable */ }
    if (title) return t("dock.ask_q.record", { title: String(title).trim().replace(/[.!?;:]+$/, "") });
  }
  const name = (x) => String(x || "").split(/[\\/]/).pop();
  const file = name(o.file_path || o.path || o.notebook_path || ((ask.content || []).find((c) => c.path) || {}).path);
  if (ask.leaves && (o.to || o.recipient)) return t("dock.ask_q.send", { to: String(o.to || o.recipient) });
  if (ask.leaves) return t("dock.ask_q.leaves");
  if (ask.kind === "edit") return file ? t("dock.ask_q.edit", { name: file }) : t("dock.ask_q.edit_any");
  if (ask.kind === "delete") return file ? t("dock.ask_q.delete", { name: file }) : t("dock.ask_q.other");
  if (ask.kind === "move") return file ? t("dock.ask_q.move", { name: file }) : t("dock.ask_q.other");
  if (ask.kind === "read" || ask.kind === "search") return t("dock.ask_q.read");
  if (ask.kind === "execute") return readsOnly(cmd) ? t("dock.ask_q.read") : t("dock.ask_q.execute");
  return t("dock.ask_q.other");
}

/** A step that only looks (lists, reads, searches, counts), so its face says so in words. */
export function readsOnly(cmd) {
  const s = String(cmd || "").trim();
  if (!s || /[;&|<>`]|\$\(/.test(s.replace(/\s2>\/dev\/null/g, "").replace(/\|\s*(head|tail|sort|wc|uniq)\b[^|;&<>`]*/g, ""))) return false;
  if (/\s-(exec|delete|ok)\b|\bsed\s+-i\b/.test(s)) return false;
  return /^(ls|cat|head|tail|wc|find|grep|rg|stat|du|file|tree|less|git\s+(status|log|diff|show))\b/.test(s);
}

/** The words that would be written, sent or run, from the change or the agent's own input; a few lines. */
function preview(ask) {
  const cut = (x) => { const s = String(x || "").trim(); const lines = s.split("\n"); const head = lines.slice(0, 6).join("\n"); return (head.length > 400 ? head.slice(0, 400) : head) + (head.length > 400 || lines.length > 6 ? "…" : ""); };
  const diff = (ask.content || []).find((c) => c.type === "diff" && withoutFrontMatter(c.new));
  if (diff) return cut(withoutFrontMatter(diff.new));
  if (ask.input) {
    try {
      const v = JSON.parse(ask.input);
      if (v && typeof v === "object") {
        for (const k of ["content", "new_string", "text", "message", "body", "url"]) if (typeof v[k] === "string" && withoutFrontMatter(v[k])) return cut(noPaths(withoutFrontMatter(v[k])));
      }
    } catch { /* not an object */ }
  }
  return "";
}

function kindWords(ctx, kind) {
  const k = "dock.kind." + (kind || "other");
  const s = ctx.t(k);
  return s.startsWith("[") ? ctx.t("dock.kind.other") : s;
}

/** A path said as its last name: "/private/tmp/…/skills/x/SKILL.md" is "SKILL.md"; a step's words
    never carry a folder, a username or a machine's layout. */
export function noPaths(text) {
  return String(text || "").replace(/(?:~|\.{1,2})?(?:\/[^\s/'"`:;,()]+){2,}\/?/g, (m) => m.replace(/\/+$/, "").split("/").pop() || m);
}

/** The words that would be written: a file's front matter (the block between --- lines at its head) is
    the machine's, never shown. */
export function withoutFrontMatter(text) {
  return String(text || "").replace(/^\s*---\n[\s\S]*?\n---\s*\n?/, "").trim();
}

/** The step in words: the change (old and new lines) and the step's own fields, each value with its
    paths said as their last names; the field names that are only a machine's (file_path, cwd) left out. */
function whatWouldHappen(ask) {
  const out = [];
  const pre = (text, cls) => {
    const p = document.createElement("pre");
    p.className = "dock-raw" + (cls ? " " + cls : "");
    p.textContent = text;
    return p;
  };
  for (const c of ask.content || []) {
    if (c.type === "diff") {
      const lines = [];
      for (const l of withoutFrontMatter(c.old).split("\n")) if (l) lines.push("− " + l);
      for (const l of withoutFrontMatter(c.new).split("\n")) if (l) lines.push("+ " + l);
      if (lines.length) out.push(pre(lines.join("\n"), "dock-diff"));
    } else if (c.type === "text" && c.text) out.push(pre(noPaths(c.text)));
  }
  if (ask.input) {
    let shown = ask.input;
    try {
      const v = JSON.parse(ask.input);
      if (v && typeof v === "object") {
        shown = Object.entries(v).filter(([k]) => !/^(file_path|path|notebook_path|cwd|dir|directory|description)$/.test(k))
          .map(([, x]) => (typeof x === "string" ? withoutFrontMatter(x) : JSON.stringify(x))).filter(Boolean).join("\n");
      }
    } catch { /* shown as it came */ }
    shown = noPaths(shown);
    if (shown.trim()) out.push(pre(shown));
  }
  return out;
}

/** A thing your agent would remember about you (the host's ask of kind `keep`: "May I remember that we
 *  go slowly?"): the one plain sentence the host made, and No · Yes in the host's words. No file, no
 *  step, no reach line: what is remembered stays in the person's own home. */
function renderKeepAsk(ctx, ask, { onAnswer }) {
  const { h } = ctx.card;
  const t = ctx.t;
  const card = h("article", { class: "card card--compact dock-ask dock-ask--keep", role: "group", "aria-label": t("dock.ask_label") });
  card.append(h("div", { class: "dock-ask-head" }, h("h3", { class: "card-title dock-ask-q" }, String(ask.question || ask.title || t("dock.ask_q.other")))));
  const said = h("p", { class: "dust", role: "status" });
  const all = [];
  const opt = (kind) => (ask.options || []).find((o) => o && o.kind === kind) || {};
  const done = (r) => { if (!r || !r.ok) { said.textContent = (r && r.reason) || t("dock.answer_failed"); for (const x of all) x.disabled = false; } };
  const no = h("button", { class: "pill dock-no", type: "button" }, opt("reject_once").name || t("dock.answer.no"));
  const yes = h("button", { class: "pill primary dock-yes", type: "button" }, opt("allow_once").name || t("dock.answer.yes"));
  all.push(no, yes);
  no.addEventListener("click", async () => { for (const x of all) x.disabled = true; done(await onAnswer("not_this")); });
  yes.addEventListener("click", async () => { for (const x of all) x.disabled = true; done(await onAnswer("yes")); });
  // the exact step: only the host's plain sentence (`ask.step`), behind one fold; the raw step
  // (`ask.raw`) is never shown, and no path, diff mark or markdown reaches her
  const step = plainStep(ask.step);
  if (step) card.append(h("details", { class: "dock-fold" }, h("summary", { class: "dust" }, t("dock.ask_exactly")), h("p", { class: "dust" }, step)));
  card.append(h("div", { class: "dock-answers" }, no, yes), said);
  return card;
}

/** The step as one plain sentence: a string (or {text}/{sentence}), with any path said by its last name
 *  and the marks of a diff or of markdown taken out; an object of the harness's own shape is not a
 *  sentence and shows nothing. */
export function plainStep(step) {
  const raw = typeof step === "string" ? step : step && typeof step === "object" && typeof (step.sentence || step.text) === "string" ? (step.sentence || step.text) : "";
  const s = noPaths(withoutFrontMatter(raw)).split("\n").map((l) => l.replace(/^\s*[-+−]\s+/, "").replace(/^#+\s*/, "").trim()).filter(Boolean).join(" ")
    .replace(/\*\*|__|`/g, "").replace(/\b(Write|Edit|Read)\s+(?=\S+\.(md|json|txt)\b)/g, "").replace(/\s+/g, " ").trim();
  if (!s || /\.(md|json|jsonl|txt|py|js)\b/i.test(s)) return s.replace(/\S+\.(md|json|jsonl|txt|py|js)\b/gi, "").replace(/\s+/g, " ").trim();
  return s;
}

/** A mark your agent proposed at your word (skills/the-chief-of-staff §5; the host's ask of kind `act`,
 *  {card_id, option_index, option, question}): "Mark Saturday morning?" over the card's own question,
 *  with **Not that** and **Yes**. Yes writes the very act the Deal writes for that answer (deal.js
 *  `actFor`, through ctx.act, undoable as any act), then answers the ask so your agent hears it; a card
 *  the Deal no longer holds marks nothing and says so. Not that answers the ask, and nothing is written. */
function renderActAsk(ctx, ask, { onAnswer }) {
  const { h } = ctx.card;
  const t = ctx.t;
  const card = h("article", { class: "card card--compact dock-ask dock-ask--act", role: "group", "aria-label": t("dock.ask_label") });
  card.append(h("div", { class: "dock-ask-head" },
    h("h3", { class: "card-title dock-ask-q" }, t("dock.ask_q.act", { option: String(ask.option || "").trim() }))));
  if (ask.question) card.append(h("p", { class: "dock-ask-why" }, ask.question));
  const said = h("p", { class: "dust", role: "status" });
  const all = [];
  const done = (r) => { if (!r || !r.ok) { said.textContent = (r && r.reason) || t("dock.answer_failed"); for (const x of all) x.disabled = false; } };
  const no = h("button", { class: "pill dock-no", type: "button" }, t("dock.ask_act_no"));
  const yes = h("button", { class: "pill primary dock-yes", type: "button" }, t("dock.ask_act_yes"));
  all.push(no, yes);
  no.addEventListener("click", async () => { for (const x of all) x.disabled = true; done(await onAnswer("not_this")); });
  yes.addEventListener("click", async () => {
    for (const x of all) x.disabled = true;
    const r = actYes(ctx, ask, (why) => { said.textContent = why; });
    if (!r.ok) { done(r); return; }
    done(await onAnswer("yes"));
  });
  card.append(h("div", { class: "dock-answers" }, no, yes), said);
  return card;
}

/** Her Yes on a mark her agent proposed: the very act the Deal writes for that answer (deal.js `actFor`,
 *  through ctx.act, undoable); a card the Deal no longer holds marks nothing. -> {ok, reason} */
export function actYes(ctx, ask, onRefused = () => {}) {
  const t = ctx.t;
  const st = ctx.state || {};
  const dc = ((st.deal && st.deal.cards) || []).find((c) => c && c.id === ask.card_id);
  const opts = (dc && dc.options) || [];
  const label = opts[ask.option_index] === ask.option ? ask.option : (opts.includes(ask.option) ? ask.option : null);
  if (!dc || !label || typeof ctx.act !== "function") return { ok: false, reason: t("dock.ask_act_gone") };
  const a0 = actFor(dc, label);
  const p = ctx.act(a0.type, a0.body, a0.links, dc.holon, { confirmed: true, label: t("dock.ask_act_marked_sr", { option: label }) });
  if (p && p.done && typeof p.done.then === "function") p.done.then((q) => { if (q && q.status === "refused") onRefused(t("dock.ask_act_gone")); });
  return { ok: true };
}

/** Her Yes on a worker her agent proposed: the worker is started (ctx.launchBody), then the ask is answered. */
export async function workerYes(ctx, ask) {
  const t = ctx.t;
  if (typeof ctx.launchBody !== "function") return { ok: false, reason: t("bodies.launch_no_host") };
  const r = await ctx.launchBody({ task: ask.task, from_card: null, confirmed: true });
  if (!r || !r.ok) return { ok: false, reason: t("bodies.launch_refused", { why: (r && r.reason) || "" }) };
  return { ok: true };
}

/** An ask as her words (the Talk draws no cards): the host's own question,
 *  else the question the card would ask; never a file, a step or a button. */
export function askWords(ctx, ask) {
  const t = ctx.t;
  if (!ask) return "";
  if (ask.kind === "worker") return t("dock.ask_q.worker", { task: String(ask.task || "").trim() });
  if (ask.kind === "act") return t("dock.ask_q.act", { option: String(ask.option || "").trim() }) + (ask.question ? " " + String(ask.question).trim() : "");
  return question(ctx, ask);
}

/** A worker your agent proposed (skills/the-chief-of-staff §4, 9; the host's ask of kind `worker`):
 *  the task in your words, where it reaches, and two answers. Start the worker is your own tap: it
 *  starts the worker (ctx.launchBody, the same yes as Task a New Worker) and then answers the ask, so
 *  your agent hears it; Not now answers the ask, and nothing is started. The cost was said in your
 *  agent's own turn just above. */
function renderWorkerAsk(ctx, ask, { onAnswer }) {
  const { h } = ctx.card;
  const t = ctx.t;
  const card = h("article", { class: "card card--compact dock-ask dock-ask--worker", role: "group", "aria-label": t("dock.ask_label") });
  card.append(h("div", { class: "dock-ask-head" },
    h("h3", { class: "card-title dock-ask-q" }, t("dock.ask_q.worker", { task: String(ask.task || "").trim() }))));
  card.append(h("p", { class: "dock-reach" }, t("dock.worker_reach")));
  const said = h("p", { class: "dust", role: "status" });
  const all = [];
  const done = (r) => { if (!r || !r.ok) { said.textContent = (r && r.reason) || t("dock.answer_failed"); for (const x of all) x.disabled = false; } };
  const no = h("button", { class: "pill dock-no", type: "button" }, t("dock.answer.not_now"));
  const yes = h("button", { class: "pill primary dock-yes", type: "button" }, t("dock.answer.start_worker"));
  all.push(no, yes);
  no.addEventListener("click", async () => { for (const x of all) x.disabled = true; done(await onAnswer("not_this")); });
  yes.addEventListener("click", async () => {
    for (const x of all) x.disabled = true;
    if (typeof ctx.launchBody !== "function") { done({ ok: false, reason: t("bodies.launch_no_host") }); return; }
    said.textContent = t("bodies.launch_starting");
    const r = await workerYes(ctx, ask);
    if (!r.ok) { done(r); return; }
    said.textContent = t("bodies.launch_started");
    done(await onAnswer("yes"));
  });
  card.append(h("div", { class: "dock-answers" }, no, yes), said);
  return card;
}

/** A worker's draft as plain lines: front matter, headings' #, list marks, emphasis, code ticks and
 *  link addresses taken out; paths said by their last name. Set as text, never as markup. */
export function plainLines(text) {
  return withoutFrontMatter(String(text || "")).split("\n")
    .map((l) => noPaths(l.replace(/^\s{0,3}#{1,6}\s+/, "").replace(/^\s*([-*+]|\d+[.)])\s+/, "").replace(/^\s*>\s?/, "")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").replace(/\*\*|__|`/g, "").replace(/(^|\s)[*_]([^*_]+)[*_](?=\s|[.,;:!?]|$)/g, "$1$2")).trim())
    .reduce((out, l) => { if (l || (out.length && out[out.length - 1])) out.push(l); return out; }, []).join("\n").trim();
}
