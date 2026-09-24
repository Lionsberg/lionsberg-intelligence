# Licensing & Attribution — LIØNSBERG Intelligence

*How the LIØNSBERG Intelligence System licenses its agents, credits what they grew from, and keeps their provenance whole. Current best understanding, revisable as the agents and the law around them mature.*

*This guide condenses and extends the **"Licensing and Attribution Handbook"** by Peter Kaminski and Freya (PKAI, 2026-06-28, CC BY 4.0). Read the original for the full reasoning.*

---

## The frame: two regimes

Value moves under one of two regimes, and licensing only makes sense in their light:

- **Commons / Flourishing** — value is created, shared, and stewarded; improvements return to the pool; provenance is honored.
- **Enclosure / Extraction** — value is captured, fenced, and rented; improvements are kept private; provenance is erased (acknowledging whose work you built on weakens the claim to own it).

LIØNSBERG is a **Commons** project. The licensing goal is **maximal openness *within* the commons, with the reciprocity and provenance that resist enclosure at the boundary.** A licence is an *impedance match* at that boundary: the continuum from permissive to reciprocal measures *how much value is obliged to return* as it crosses toward extraction.

## An agent is a stack of layers

There is no single licence for an agent. A personal AI agent is a bundle of distinct things, each crossing the boundary differently and needing its own match. License **per layer**:

| Layer | What it is | The kind of law | LIØNSBERG's choice |
|---|---|---|---|
| **Machinery — code** | runtime, scripts, tooling | software licence (MIT→Apache→MPL→GPL→**AGPL**) | **MPL-2.0**, the licence of the starter kit the agents grew from (the code is minimal; the runtime is Claude Code). **AGPL-3.0** is the honest match *if a hosted runtime is ever shipped* — it closes the network boundary that plain GPL leaves open. |
| **Knowledge — writing** | the corpus, strategy, and documents the agent carries | content licence (Creative Commons) | **CC BY-SA 4.0** — share-alike is the reciprocity match; adaptations return to the commons. |
| **Prompts / config** | charter, skills, agent configuration (the gray zone) | *decide code-or-content, and say so* | **treated as code → MPL-2.0.** Skills and prompts travel as code. |
| **Name / persona** | what the agent is *called* and *is* | trademark and stewardship (not a licence) | **stewarded.** "LIØNSBERG", "Player+", and the names of agents are not licensed for reuse. Fork the code and the writing freely; do not pass a derivative off as the official project or misrepresent it. Open code and knowledge, protected name (the Firefox / Linux pattern). |

**Why not CC0** for the knowledge layer: CC0 removes reciprocity and lets knowledge be enclosed with nothing flowing back. More permissive toward extraction is not more aligned. Share-alike is the intentional commons choice.

**Obligations bite on *sharing*, not testing.** Nearly all return-obligations (GPL, AGPL, MPL, CC BY-SA) trigger on distribution or on hosting for others; private use and testing are unencumbered.

## Provenance: artifact → ledger → proof

A licence can *require* attribution; only a culture *preserves* it, and provenance is exactly what extraction erases. So it is made operational, in three levels:

1. **A travelling file.** Every agent carries an append-only record of what it grew from, which travels with it through forks (the `grows_from` chain). Player+ carries it as `LINEAGE.md`, and each skill carries its own. Necessary, but weak alone — a claim anyone can delete.
2. **A shared ledger.** Record the chain in an append-only place many parties hold, so erasing one copy no longer erases the fact.
3. **Proof.** Content hashes, **signed commits**, trusted timestamps — provable on demand, not merely asserted. Git already gives much of this; prefer signed commits when contributing.

## The rules we keep

1. **License every agent per layer**, with an SPDX line for the software and content layers (e.g. `MPL-2.0 AND CC-BY-SA-4.0`) and a clear name policy for the persona layer.
2. **Carry the lineage file** in every agent; append, never rewrite; carry it into derivatives.
3. **Build every general agent clean** — no one person's identity or working history inside it; publish from a fresh history.
4. **Private first; public when reviewed.** Publishing is the step that cannot be undone.
5. **Revisit as the agents grow.** When an agent ships hosted code, revisit AGPL; as the line scales, stand up the ledger and adopt proof.

---

*Adapted under CC BY 4.0 from Peter Kaminski and Freya, "Licensing and Attribution Handbook" (2026-06-28). This adaptation © LIØNSBERG, offered under CC BY-SA 4.0.*
