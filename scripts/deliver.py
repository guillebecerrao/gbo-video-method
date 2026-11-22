"""Deliver a new version: keep only the current one in entregas/, archive the older ones in entregas/anteriores/.

Folder template (SKILL.md § Estructura de carpeta por video; Frameback PROTOCOL §9.2): every render the creator reviews lives in
`entregas/` (the current version of each artifact + its variants). When vNN+1 is delivered, vNN moves to
`entregas/anteriores/` together with its sidecars (`.srt`, `.timeline.json`, `.script.json`, any `<stem>.*`) and its
Frameback review dir `entregas/review/<stem>/`, so the review keeps playing its video.

Usage (from the project folder; stdlib only, no venv needed):
    python3 edit/deliver.py entregas/ia_charla-agentes_reel_v02.mp4 --dry-run   # show the plan, move nothing
    python3 edit/deliver.py entregas/ia_charla-agentes_reel_v02.mp4             # archive v01 (+ sidecars + review)

The new file must already be in entregas/ and follow references/nombres.md. Every older version of the same
artifact (same topic, situation, piece and artifact; any variant) is archived. The new version's own variants
(same vNN) stay.

Safety: only moves (never deletes, renames or overwrites); checks every destination before moving anything; refuses
symlinks, other volumes and anything under final/ or .frameback/ (Frameback writes those). If the old version has
a Frameback review and the new one does not yet, it refuses: open the new version in Frameback first
(`frameback open entregas/<new>`) so the comments carry over, or pass --no-review-check.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PART = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ASSET_RE = re.compile(
    rf"^(?P<topic>{PART})_(?P<situation>{PART})_(?P<piece>(?:reel|yt|feed)(?:-[1-9][0-9]*-{PART})?)"
    r"(?:_(?P<artifact>cover-9x16|cover-4x5|thumb-16x9|post))?(?:_(?P<variant>[a-z]))?"
    r"_v(?P<n>[0-9]{2,})\.(?P<ext>[a-z0-9]+(?:\.[a-z0-9]+)*)$"
)
DEFAULT_LAYOUT = {"deliveries": "entregas", "previous": "entregas/anteriores", "final": "final"}
FORBIDDEN = (".frameback",)


def parse(name: str):
    m = ASSET_RE.match(name)
    if not m:
        return None
    d = m.groupdict()
    stem = name[: -(len(d["ext"]) + 1)]
    return {"key": (d["topic"], d["situation"], d["piece"], d["artifact"] or ""), "n": int(d["n"]), "stem": stem}


def project_layout(project: Path) -> dict:
    layout = dict(DEFAULT_LAYOUT)
    manifest = next((m for m in (project / "proyecto.json", project / "frameback.project.json") if m.is_file()), None)
    if manifest:
        try:
            data = json.loads(manifest.read_text())
            for k in DEFAULT_LAYOUT:
                v = (data.get("layout") or {}).get(k)
                if isinstance(v, str) and v and not v.startswith("/") and ".." not in v.split("/"):
                    layout[k] = v
        except (ValueError, OSError):
            pass  # invalid manifest: Frameback treats it as no template; defaults still apply
    return layout


def fail(msg: str) -> None:
    print(f"deliver: {msg}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("new", type=Path, help="the new version, already in entregas/")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, move nothing")
    ap.add_argument("--no-review-check", action="store_true",
                    help="archive even if the old version has a Frameback review and the new one does not")
    a = ap.parse_args()

    new = a.new.absolute()
    if new.is_symlink() or not new.is_file():
        fail(f"not a regular file: {a.new}")
    deliveries = new.parent
    # the project is the nearest folder with a manifest (a custom layout may nest entregas/), else the parent
    project = next((d for d in list(deliveries.parents)[:3] if (d / "proyecto.json").is_file() or (d / "frameback.project.json").is_file()), deliveries.parent)
    layout = project_layout(project)
    if deliveries.resolve() != (project / layout["deliveries"]).resolve():
        fail(f"{a.new} is not directly in the deliveries folder ({layout['deliveries']}/)")
    prev_dir = project / layout["previous"]
    final_dir = (project / layout["final"]).resolve()
    for p in (deliveries, prev_dir):
        r = p.resolve() if p.exists() else p.absolute()
        if r == final_dir or final_dir in r.parents or any(s in FORBIDDEN for s in r.parts):
            fail(f"refusing to write in {p} (final/ and .frameback/ belong to Frameback)")

    me = parse(new.name)
    if not me:
        fail(f"{new.name} does not follow references/nombres.md (needs …_vNN.<ext>)")

    # older versions of the same artifact, grouped by stem (a stem = the asset + all its `<stem>.*` sidecars)
    stems: dict[str, int] = {}
    for f in deliveries.iterdir():
        info = parse(f.name)
        if not info or info["key"] != me["key"] or f.is_dir():
            continue
        if info["n"] > me["n"]:
            fail(f"{f.name} is newer than {new.name}: deliver the newest version")
        if info["n"] < me["n"]:
            stems[info["stem"]] = info["n"]
    if not stems:
        print(f"deliver: nothing to archive; {new.name} is the only version in {layout['deliveries']}/")
        return

    moves: list[tuple[Path, Path]] = []
    review_root = deliveries / "review"
    for stem in sorted(stems):
        for f in sorted(deliveries.iterdir()):
            if f.name.startswith(stem + ".") and not f.is_dir():
                moves.append((f, prev_dir / f.name))
        rdir = review_root / stem
        if rdir.is_dir():
            if not a.no_review_check and not (review_root / me["stem"]).is_dir():
                fail(f"{stem} has a Frameback review but {me['stem']} does not yet: open the new version first "
                     f"(frameback open {layout['deliveries']}/{new.name}) so comments carry over, "
                     f"or pass --no-review-check")
            moves.append((rdir, prev_dir / "review" / stem))

    dev = os.stat(deliveries).st_dev
    for src, dst in moves:
        if src.is_symlink():
            fail(f"refusing to move a symlink: {src.relative_to(project)}")
        if os.lstat(src).st_dev != dev:
            fail(f"{src.relative_to(project)} is on another volume; move it by hand")
        if dst.exists() or dst.is_symlink():
            fail(f"destination exists, nothing moved: {dst.relative_to(project)}")
    if prev_dir.exists() and os.stat(prev_dir).st_dev != dev:
        fail(f"{layout['previous']}/ is on another volume; nothing moved")

    for src, dst in moves:
        print(f"{'would move' if a.dry_run else 'move'}: {src.relative_to(project)} -> {dst.relative_to(project)}")
        if a.dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():  # raced in after the check
            fail(f"destination appeared, stopped: {dst.relative_to(project)}")
        os.rename(src, dst)
    if not a.dry_run:
        print(f"deliver: current = {layout['deliveries']}/{new.name}; archived {len(stems)} version(s)")


if __name__ == "__main__":
    main()
