<!-- Player+ — how the character matrix's defaults are measured. Part of Player+; credit and licences: LINEAGE.md. -->

# Measuring the matrix's defaults

A character matrix names, for each axis, a **default**: where the base model and its host sit when nothing is said. Until it is measured, a default is a guess. This folder is the instrument that turns the guess into a measurement. It runs no model itself; a run is played by hand or by a script of your own, and this folder holds the scenarios and folds the ratings.

## What is measured

Each numeric axis of the companion's matrix has one fixed scenario in `scenarios.json`: a short exchange a person might bring, the axis it probes, and two tells, each the far end of its own pole alone, in words the matrix does not use. A target between the ends is then rated between them. The kept row (Harm-avoidance) has a word for its target, not a number, so it is not rated. A changed scenario starts a new series.

A run plays every scenario through the persona four ways:

1. with the matrix absent, at a fresh start;
2. with the matrix absent, after a compaction or at a long context;
3. with the matrix loaded, at a fresh start;
4. with the matrix loaded, after a compaction or at a long context.

A transcript holds only the scenario's exchange and the persona's answer, whatever came before it in a long context. Each is saved as `<id>.md` or `<id>.txt` under a random id (for example sixteen hex digits), so no id says its condition; an id with a condition word in it is named as a leak. The run's key, `key.json`, sits beside them and names the model, the host, the date and the window; for each id its axis, its matrix (`absent` or `loaded`) and its context (`fresh` or `long`); and in `flipped` the axes whose tells the sheet shows the other way round (about half, chosen at random).

## Who rates

**An independent reader**: an agent or a person who did not play the run and has no stake in the matrix. The reader sees only the transcripts and the reader's sheet, never the key. The sheet shows each id with its scale and two tells under the neutral labels A and B: no axis name, no pole name, no condition. Which pole is A is kept in the key, apart from the sheet. For each transcript the reader gives a number from A to B (−100 to +100, or 0 to 100) and one line of why.

    python3 -I measure.py RUN_FOLDER --sheet

The ratings file is JSON, one object per rating: `{"transcript": "9f2c41d07ab3e655", "rating": -30, "why": "one line", "reader": "agent:reader"}`.

## The fold

    python3 -I measure.py RUN_FOLDER RATINGS.json            # the table as JSON
    python3 -I measure.py RUN_FOLDER RATINGS.json --markdown # the table as rows for the matrix

Per axis: **default**, the mean with the matrix absent; **held**, the mean with it loaded; **delta**, held minus default, with its sign; **to target**, held minus the matrix's target; **drift**, held after a long context minus held at a fresh start, which shows how far the default pulls back under load.

An axis with no ratings says so in words and carries no number; an axis in the key with no scenario is named. A rating that is not a number on the scale, has no why, names a transcript the key does not hold, or is a second rating of one transcript by one reader is set aside and listed. The same ratings in any order give the same table.

## What a default is

**A number without its model, host, date and window is not a default.** A default belongs to one model in one host at one context window on one date, and moves with each. The table's status is `measured` only when the key names all four and at least one axis has a default; otherwise it is `not a default`. When a run lands, the matrix's Default column takes the measured numbers and its status line names the four; until then every default in the matrix is an estimate.

The carrier's matrix has axes of its own (fidelity to the Seed, provenance, scope); its scenarios are not yet written; when they are, they go in a file beside this one and fold the same way with `--scenarios` and `--matrix`.
