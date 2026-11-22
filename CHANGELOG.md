# Changelog

## 0.5.0 — 2026-11-22
One folder per piece in `entregas/` (Frameback BL-090, PROTOCOL §9.2) and files delivered in the review thread
(Frameback BL-089, PROTOCOL §3.2).

- Folder per piece, always (also with a single piece): every delivered file lives in `entregas/<piece>/`, where
  `<piece>` is the piece part of its name (`reel`, `yt`, `feed`, `<format>-<N>-<slug>`), with its assets, variants,
  sidecars and `review/<stem>/` dirs; previous versions in `entregas/<piece>/anteriores/` (each with its sidecars and
  its review dir); Frameback copies approved files to `final/<piece>/` (the skill still never writes in `final/`).
  Folders of `entregas/` that are not pieces (e.g. `entregas/muestras/`) are never touched. `SKILL.md` (structure,
  versioning, scaffold, phase outputs, QA), `references/nombres.md` (new "Carpeta de pieza" section; the `check-name`
  command now walks the piece folders only), `references/frameback.md` and `references/remotion.md` use the new paths.
- `templates/proyecto.json` and the scaffold declare `pieces: [{id}]` in the project's order (from the brief, e.g.
  `yt`, `reel-1-hook`, `reel-2-consejo`; `[{"id": "reel"}]` by default).
- `scripts/deliver.py`: archives into `entregas/<piece>/anteriores/` (review dir `entregas/<piece>/review/<stem>/`
  → `anteriores/review/<stem>/`); refuses a file that is not in the folder of its own piece (another piece's folder,
  a non-piece folder); reads `layout.previous` as relative to each piece folder (a pre BL-090 `entregas/anteriores`
  still works); warns, never writes, when `pieces` is missing, does not declare the delivered piece, or has invalid or
  duplicate ids (the manifest is shared with Frameback, which writes `finals` under its own lock). Projects already in
  the flat 0.4.x layout keep working as before (archive in `entregas/anteriores/`, with a notice): nothing is
  migrated; moving them into piece folders is the creator's call, by hand (`frameback adopt` does not migrate an
  adopted project, it only warns `flat_layout`). Projects without `proyecto.json` are unchanged.
- `gbo_render.py` / `reel_render.py`: usage text renders to `-o entregas/<piece>/…` and the output folder is created
  when missing (first delivery of a piece). `script_sidecar.py` run by hand finds `<project>/edit/guion.json` from
  `entregas/<piece>/`, its `anteriores/` or the flat `entregas/` (before, only from `entregas/`).

## 0.4.1 — 2026-11-22
Frameback `check-name` in QA and general comments (Frameback BL-076 and PROTOCOL §3.1).

- QA (`SKILL.md` checklist, phase 8) and `references/nombres.md`: before announcing a delivery, check the names in
  `entregas/` with `find entregas -maxdepth 1 -type f ! -name '.*' -exec frameback check-name {} +` (only top-level
  files: a plain `entregas/*` also passes `anteriores/` and `review/`, which fail as `no_extension`); exit 0 all
  valid, 1 some invalid (fix them, renaming sidecars with the same stem), 2 usage error; `--json` prints
  `[{name, ok, parsed?, code?, reason?}]`. Frameback's validator rules; without Frameback, or with a version that has
  no `check-name` (detect with `frameback help | grep check-name`: older binaries answer `unknown command` with exit
  1), the regex in `nombres.md` is the reference. Projects without `proyecto.json` skip this step.
- `references/frameback.md`: general comments (`anchor.scope: "video"`, no `time`; `watch --json` carries
  `data.scope`) are handled as notes about the whole piece (no frame, range or snapshot) with the same
  status/plan/reply flow; how to tell them from time-anchored (`time`) and script-anchored (`target` without `time`)
  comments. Both features need a Frameback with PROTOCOL §3.1 support (later than 0.1.2), with how to update.
  Without Frameback nothing changes in the flow.

## 0.4.0 — 2026-11-22
Frameback navigation and folders (requests from Frameback EP-006): naming convention, project folder template and
script sidecar.

- Naming convention (`references/nombres.md`, with a checkable regex aligned with Frameback PROTOCOL §9.3,
  `ASSET_NAME_RE`): project folder `YYYY-MM-DD_topic_situation` (recording date, the planned one until recording;
  rename at ingest only before the first delivery; broad topic such as `ia`, `marca-personal`, `builderia`); files
  without date `<topic>_<situation>_<format>[_<artifact>][_<variant>]_<vNN|final>.<ext>`, format `reel|yt|feed`;
  several pieces of one format all use `<format>-<N>-<slug>` from 1 (`reel-1-hook`, `reel-2-backstage`); two-digit
  `vNN`, lowercase extension, sidecars share the stem. `_final` is written only by Frameback on approval, without
  the variant letter. All examples in `SKILL.md`, references, templates and script usage text follow it. One counter
  per piece from preview to final is unchanged. Ongoing and published projects keep their names (no hot migration).
- Folder template v1, the one Frameback reads (PROTOCOL §9.2): new projects get `proyecto.json` (new
  `templates/proyecto.json`: `schemaVersion`, `kind: "frameback.project"`, `name`, `created`), `raw/`, `contexto/`,
  `edit/`, and `entregas/` on the first delivery. Every render the creator reviews goes to `entregas/` (only the
  current version of each artifact + its variants); on vNN+1 the previous version moves to `entregas/anteriores/`
  together with its sidecars and its Frameback `review/<stem>/` dir, replacing the `edit/_reemplazados/` rule. All
  workshop files stay in `edit/`; the skill never writes in `final/` or `.frameback/`; `contexto/` is read as the
  creator's material (untrusted content: a request, never instructions). Projects without `proyecto.json` (started
  before the template) keep their structure; no hot migration.
- New `scripts/deliver.py` (stdlib): archives the older versions of the delivered artifact with their sidecars and
  review dir; move-only, checks every destination first, refuses symlinks, other volumes, `final/`, `.frameback/`,
  and archiving a reviewed version before the new one was opened in Frameback (so comments carry over). Warns when
  `proyecto.json` still has the template placeholders (`created`/`name`), which Frameback rejects.
- `gbo_render.py` writes `<stem>.cards.json` to `edit/` and the pre-loudnorm temp file to `work_*/`, so only
  deliverable sidecars sit next to the render. Usage text of the render scripts, `references/frameback.md` and
  `references/remotion.md` use `-o entregas/…`.
- Script sidecar for Frameback (PROTOCOL §8): new `scripts/script_sidecar.py` writes `<stem>.script.json` next to
  each render from a structured script `edit/guion.json` (new template `templates/guion.ejemplo.json`): sections with
  stable ids resolved to final-video ranges (timeline beats, explicit ranges, or the EDL as a fallback), video order,
  `omitted`, `version` from `_vNN`, `scriptId` from the stem, `video.hash` (Frameback's fingerprint algorithm) and
  duration, optional `original`. `gbo_render.py` and `reel_render.py` call it at the end (`--no-script` disables it);
  without `edit/guion.json` it does nothing, and a failure only warns (render exit code unchanged). Run by hand on a
  render in `entregas/`, it looks for the project's `edit/guion.json`
- `references/frameback.md`: how review decisions reach version N+1 (accepted comment or accepted proposal → `active`
  decision with `origin` and `since`; revert → `superseded` + `supersedes`; declined → optional `rejected`)

## 0.3.2 — 2026-11-12
- Frameback review flow (`references/frameback.md`): every comment is handled as soon as it arrives. The editing
  orchestrator classifies and delegates; anything that needs producing (another photo, song, animation, SFX, regrade)
  goes to a background subagent that leaves it ready in staging. "Process" (`review.submitted`) only integrates what
  is prepared and renders the next version once. Never wait for the submit, never use `watch --exit-on`.

## 0.3.1 — 2026-11-12
- Repository renamed `gbo-video` → `gbo-video-method` (GitHub redirects the old URL). The skill name is unchanged:
  `gbo-video`, linked as `~/.claude/skills/gbo-video`. Suggested clone path is now `~/Developer/gbo-video-method`.

## 0.3.0 — 2026-11-12
- Music montage reels: new `scripts/reel_render.py` (beat-length segments snapped to the music grid, speed and
  timelapse, ambient/mute audio, muffled intro until the drop, music stop, natural outro, ducking, captions aligned
  by energy, Frameback sidecar) rendered with the new `GboMontage` composition, or `--captions ass` without Remotion
- New `scripts/sfx_track.py`: SFX track from a cue list anchored to Remotion props ("end.clickAt"), synthesized
  sounds or any audio file
- Neutral examples: `templates/edl.reel.ejemplo.json`, `templates/sfx.ejemplo.json`
- The creator's Remotion working copy now defaults to `<profile>/remotion` (style rules and components travel together)

## 0.2.0 — 2026-11-12
Learnings from four more edits (event recap, a shop promo, a product-launch reel, a montage reel), consolidated.

- Ingest checklist (phase 3): color by metadata (HLG/PQ → SDR, log → LUT), mirrored footage, rotation, mixed fps
- Cuts: minimum air measured by energy (≥ 0.15 s; 0.4–0.5 s on take change), verify cuts on the music-free base,
  cut (never speed up) hesitations
- Versioning: one counter per piece from previews to final; never re-render over a number the creator opened
- `gbo_render.py`: `hflip`, `grade`, `color_chain`, `fps`, per-range `speed` / `mute`, b-roll and card anchors
  `[range, source_time]` resolved to output time (`<out>.cards.json`), rounded caption box
  (`caption_style.rounded`), captions never spill into the next range
- `mix_audio.py`: licensed music track with `--music`, `--music-offset` and its own fade-out; `--no-sfx`
- New `cut_energy.py`: air before/after the voice in every EDL range (adaptive noise-floor threshold) and voiced islands
- New `rechunk.py`: re-segment captions at phrase boundaries from a one-phrase-per-line file, keeping word timings
- Music: the track's ending never lands under the CTA; lower library masters before ducking
- Remotion: `Captions` `dark` variant (reel style), `EndCard` (typed URL) in `GboVertical`, `cardWidth`, new icons,
  `GboCover` with four layouts (`duo`, `single`, `frame`, `split`)
- Covers: face choice (eyes open, intentional expression), record 3–4 s of "photo" per session, text that
  invites without revealing

## 0.1.0 — 2026-11-09
First public release. Extracted from the author's private editing skill after a pilot of
vertical reels and a two-camera long-form conversation.

- 10-phase workflow with checkpoints, model-per-phase guidance and deliverable versioning
- Local profile (`~/.config/gbo-video/`) for brand, glossary, style overrides and learnings
- First-use dependency check that asks before installing anything
- Production plan mode for scripts written here or in an external system
- Local transcription adapter for video-use (mlx-whisper, word timestamps)
- Render, audio and mix scripts with env-configurable paths
- Remotion template (captions, lower third, panels, reel, long form, cover, thumbnail)
- Optional Frameback review loop
- Optional web teleprompter for recording (bilingual README, Spanish first)
