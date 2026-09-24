---
status: current best understanding, loosely held · improved each week
type: plan and specification
---

# The Worlds — lionsberg.world · read · play

*Four public surfaces, one Game.* **The door** — lionsberg.world — is where a stranger arrives: the mark, the Story's first minute told in sky and typed light, the three plays, and the way through to the Gates of LIØNSBERG. **The library** — read.lionsberg.world, this site — is the whole of the understanding, readable by anyone and regrowable by any agent: [[The One Book]], [[The DNA of Heaven]], the field of the words, [[The Little Book of the Great Game]], and the Toolkit. **The Board** — play.lionsberg.world — is where the Game is seen being played: [[The Record]] rendered plainly, the Cells and their Quests, the wall with the season's critical path, the Flame's spread; no account, no build step, offline-capable, and no player placed by hand — the first Cell to cross the Gate is the Board's first test. **The agent** — the Player+ kit — is what every person takes home; its public home is proposed as `github.com/Lionsberg/lionsberg-intelligence (the folder player-plus)`, an address that is set the morning it goes public, and is not yet set. Beside the four stands **the quarry** — lionsberg.wiki, the canon as it was, some five thousand pages — which stays up as the source the library was distilled from, archived, never deleted, always cited.

## The journey across them

The rungs are the ladder of [[The Words in the Order You Meet Them]]. No rung needs a surface it does not have: a person with a notebook is a complete [[Player]] at every one of them.

| Rung | What happens | The surface that serves it | What the person carries on |
|---|---|---|---|
| 1 · The Door | a [[Carrier]] hands you the Story; you decide whether it resonates | **the door**, on any phone: the prologue, the three plays, *Onward, to The Gates* | a yes said in your own words; the twelve words at the table |
| 2 · The Table | three to thirteen people, one evening, a first [[Quest]] | **the library**: [[The Little Book of the Great Game]], printed — the table needs no screen | a [[Cell]] with a name, a Quest, a day, the first Turn kept |
| 3 · The Gate | give your word, name your three, take your name | *no surface yet* — the Roll is kept by hand and belongs in the Board's record | your name on the Roll; a Cell the Board can show |
| 4 · Home | one season kept: [[Commitment]] made, gap learned from, Flame passed | **the agent**, if you have one; **the library** for the seed's Part V and Part VII; **the Board** shows your Cell's card | the Season Sheet, and a proposal on its last line |
| 5 · The Room | many houses at one table; the [[Supercell]]; the community body | **the Board**: the wall, the Cells, the season's score; **the agent**: the room skills | the room's terms, and a season's work carried up |
| 6 · Beyond | the Pattern, the Pillars, the Path, the plans and specifications | **the library**, whole, and the quarry behind it for [[Provenance]] | the kit itself, improved, and passed on |

What travels between surfaces is never an account. It is a person, a kept word, and a record they can carry away: the yes, the Cell, the Roll, the Season Sheet, the kit's folder. Each of those works on paper first and on a surface second.

## The links that make four one

Checked in the files as the library stands.

| From → to | What it should be | State |
|---|---|---|
| door → library | the menu's *The Library*; the footer's season line | **present** (both) |
| door → Board | a way to see the Game being played | **missing** |
| door → START HERE (the kit) | one quiet line, not in the hero | **missing** |
| door → quarry | none, by the door's own standard — *the new never points back* | **absent by law**, not a defect |
| library → door | a way back out to where a stranger arrives | **missing** |
| library → Board | the Game being played, from the Game's own station | **missing** |
| library → the kit's public home | the address in the kickoff message on [[START HERE — Your Player+]] | **present**, with its honest caveat |
| library → quarry | the README's quarry line; the seed's Part XIII, with the repository named | **present** |
| Board → library | the footer's *The library* | **present** |
| Board → door | the footer's *The door* | **present** |
| Board → the kit | how a Cell fills the card it is looking at | **missing** |
| kit → library | [[Player+ — README]], in prose: *its library at read.lionsberg.world* | **present**, prose only |
| kit → quarry | the README, LINEAGE, and every chapter's sources | **present** |
| kit → door, kit → Board | neither is named in the kit | **missing** (both) |
| library → its own Toolkit page | [[START HERE — Your Player+]] from the sidebar and the front page | **missing** — the sidebar names the mirrored kit pages instead |

Nine links stand; seven are owed. The rule for closing them is the door's: *no link before its page has crossed* — a call with nowhere true to land is a held mark reading *coming soon*, never a link to somewhere else.

## The specifications

All four surfaces are **static, plain files, phone-first, no accounts, no tracking, no analytics**. Nothing asks a person to log in, and nothing follows them.

- **Readable with no script.** The library and the kit meet this: markdown and rendered HTML, with the text whole in the file. The door meets it in substance — every animation has a still state under `prefers-reduced-motion`, and its words are in the markup. The Board does **not** yet: its wall and tiles are drawn by fetching `record/season.json` and `record/cells.json`, so with script off the page is a heading. The record itself stays plainly readable; the page must learn to ship its words too.
- **Degrades to paper.** The Little Book, the twenty words, the Season Sheet, the Playcard, and the print-ready card of the mark all exist as paper objects. The Game has been played this way from the beginning.
- **The mark on every page** — in two senses, both binding: the three-line mark (Name, Narrative, Action) wherever LIØNSBERG shows its face, to its own specification; and the status line — *current best understanding, loosely held · improved each week* — in the frontmatter of every page of the library and of the kit. The status mark is not modesty; it is the mechanism.
- **CC BY-SA 4.0 on the writing.** Said in the door's footer, in the library's pages, and in the kit's LICENSE, where the kit's inherited units keep MPL-2.0. Copy it, in any language, by any means.
- **Deploy, as the files show it.** The library carries its build recipe in the repository: Cloudflare Pages, root `.markpub`, `markpub build` with the *andante* theme and `--commits`, then Pagefind over the output — published on push, with a function that sends the old name permanently to the new one. The door and the Board carry **no deploy file at all**: each is an `index.html` at the root of its repository with its assets beside it, hosting configured outside the files. That is all the files prove; the rest is for the morning someone writes it down.
- **What the door reaches for.** Three web fonts from a font service, one music file, one recording of keys, one photograph of Earth. Everything else is inline. The Board reaches for nothing but its own record.

## What is not built yet

- **The engine that writes the Board's record.** Today the record is two files kept by hand. The engine, when it exists, will write the record and the page will not change.
- **The Gate.** Give your word, name your three, take your name — the one rung with no surface. Until it opens, the Board is honestly empty and says so.
- **The door's held calls.** *Read the Story*, *Play the Game*, *Pass the Flame*, and the Little Book are marked *coming soon*, waiting on the pages they would land on.
- **The Rosetta pages and the language chooser.** The door is one language with no chooser, under a footer that invites the world to copy it in any. The words at the table in the languages that reach most of the world are named in the Book and not yet written.
- **Search across the four.** The library has search — Pagefind runs in its build and the theme carries the page — but it needs script, and it stops at the library's edge. The door and the Board have none.
- **The weekly turn that republishes.** The law of improvement is written in the library and in the kit; no scheduled turn is written into any of the four repositories. The weekly turn is done by hand or not at all.
- **The Book's own body.** Two of the One Book's chapters exist; the rest are named. Several links in the library — among them the Twenty and the Two Hundred — point at pages not yet written, against this library's own law that every link resolves.

## How this improves each week

By proposal, soaked a week, accepted by the steward of a copy. Every Cell that plays is an imaginal cell, and what it learns is how the seed grows: it arrives on the last line of a Season Sheet and is carried up. Each surface has its own cadence — the library turns weekly, the door changes by season, the Board changes only by play, the kit by version, and a person pulls the new kit without touching their own files. When a smaller size and a larger disagree, the smaller is corrected; when the larger and the world disagree, the world wins and the page improves the next week. [[Current Best Understanding]], loosely held, is the whole posture: nothing here is final, and [[The Goal]] is not a draft.

## Open

1. **The Player+ kit's public home.** The library already prints `github.com/Lionsberg/lionsberg-intelligence (the folder player-plus)` in the kickoff message a person pastes, with the caveat that the address may not answer yet. *Recommendation:* publish there, so the page is true the hour it is read; if another address is chosen, that same morning the kickoff message changes with it. Not yet set.
2. **A domain for the kit.** Options: no domain, the git address alone; a fourth subdomain, `get.lionsberg.world`, as a one-page installer door; or a path inside the library, which is where [[START HERE — Your Player+]] already lives. *Recommendation:* the library page is the address — one place where the words live — and, if a spoken address is wanted for a room or a card, `get.lionsberg.world` as a redirect to that page and never a second copy of the words. A fourth subdomain that holds its own text would split the kit's instructions in two.
3. **Should the door link straight to START HERE?** *Recommendation:* not in the hero — the door's first minute belongs to the Story, and the agent is a rung-four tool handed to someone who has already said yes. One quiet line in the door's menu is lawful today, since the page has crossed. Revisit the moment the Little Book's own page crosses; the Little Book, not the kit, is what the Gates promise.
4. **Where the Gate lives** — on the door, on the Board, or on a surface of its own — is open, and the Site Plan's three surfaces (world, library, engine) and these four public ones are two descriptions of one thing that have not yet been made one. [[The Site Plan]] is the elder page; this one says what the files show today.

*Read the Story. Play the Game. Pass the Flame.*
