"""Deliver a new version: keep only the current one in entregas/<piece>/, archive the older ones in entregas/<piece>/anteriores/.

Folder template (SKILL.md § Estructura de carpeta por video; Frameback PROTOCOL §9.2, BL-090): every piece has its own
folder, also when the project has a single piece. `entregas/<piece>/` (`<piece>` = the piece part of the name:
reel | yt | feed | <format>-<N>-<slug>) holds the current version of each artifact of that piece + its variants. When
vNN+1 is delivered, vNN moves to `entregas/<piece>/anteriores/` together with its sidecars (`.srt`, `.timeline.json`,
`.script.json`, any `<stem>.*`) and its Frameback review dir `entregas/<piece>/review/<stem>/`, so the review keeps
playing its video and the `previous` chain keeps working.

Usage (from the project folder; stdlib only, no venv needed):
    python3 edit/deliver.py entregas/reel/ia_charla-agentes_reel_v02.mp4 --dry-run   # show the plan, move nothing
    python3 edit/deliver.py entregas/reel/ia_charla-agentes_reel_v02.mp4             # archive v01 (+ sidecars + review)
    python3 edit/deliver.py entregas/reel-1-hook/ia_charla_reel-1-hook_v03.mp4       # one of several reels

The new file must already be in its piece folder and follow references/nombres.md. Every older version of the same
artifact (same topic, situation, piece and artifact; any variant) is archived. The new version's own variants
(same vNN) stay. Folders of entregas/ that are not piece folders (e.g. entregas/muestras/) are never touched.
Projects still in the flat layout of 0.4.x (files directly in entregas/) keep working as before (archive in
entregas/anteriores/): nothing is migrated here.

Safety: only moves (never deletes, renames or overwrites); checks every destination before moving anything; refuses
symlinks, other volumes and anything under final/ or .frameback/ (Frameback writes those). If the old version has
a Frameback review and the new one does not yet, it refuses: open the new version in Frameback first
(`frameback open entregas/<piece>/<new>`) so the comments carry over, or pass --no-review-check. It never writes
proyecto.json (Frameback writes `finals` there under its own lock); it only warns when the manifest needs a fix.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PART = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PIECE = rf"(?:reel|yt|feed)(?:-[1-9][0-9]*-{PART})?"
PIECE_RE = re.compile(rf"^{PIECE}$")
ASSET_RE = re.compile(
    rf"^(?P<topic>{PART})_(?P<situation>{PART})_(?P<piece>{PIECE})"
    r"(?:_(?P<artifact>cover-9x16|cover-4x5|thumb-16x9|post))?(?:_(?P<variant>[a-z]))?"
    r"_v(?P<n>[0-9]{2,})\.(?P<ext>[a-z0-9]+(?:\.[a-z0-9]+)*)$"
)
# `previous` is relative to each piece folder (PROTOCOL §9.1); a pre BL-090 value "entregas/anteriores" reads as "anteriores"
DEFAULT_LAYOUT = {"deliveries": "entregas", "previous": "anteriores", "final": "final"}
FORBIDDEN = (".frameback",)
MANIFESTS = ("proyecto.json", "frameback.project.json")


def parse(name: str):
    m = ASSET_RE.match(name)
    if not m:
        return None
    d = m.groupdict()
    stem = name[: -(len(d["ext"]) + 1)]
    return {"key": (d["topic"], d["situation"], d["piece"], d["artifact"] or ""), "n": int(d["n"]), "stem": stem,
            "piece": d["piece"]}


def warn(msg: str) -> None:
    print(f"deliver: aviso: {msg}", file=sys.stderr)


def check_manifest(manifest: Path, data: dict) -> None:
    """Warn (never fix, never fail) when the manifest would not pass Frameback's validation."""
    import datetime as _dt
    problems = []
    try:
        _dt.date.fromisoformat(str(data.get("created", "")))
    except ValueError:
        problems.append(f"created={data.get('created')!r} no es una fecha AAAA-MM-DD real")
    if not isinstance(data.get("name"), str) or not data["name"].strip() or "<" in data["name"]:
        problems.append(f"name={data.get('name')!r} sigue con el placeholder de la plantilla")
    pieces = data.get("pieces")
    if pieces is not None:
        if not isinstance(pieces, list) or not all(isinstance(p, dict) for p in pieces):
            problems.append('pieces debe ser una lista [{"id": …}]')
        else:
            ids = [p.get("id") for p in pieces]
            bad = [i for i in ids if not isinstance(i, str) or not PIECE_RE.match(i)]
            if bad:
                problems.append(f"pieces con id inválido {bad!r} (reel|yt|feed o <formato>-<N>-<slug>)")
            dup = sorted({i for i in ids if isinstance(i, str) and ids.count(i) > 1})
            if dup:
                problems.append(f"pieces repite {dup!r}")
    if problems:
        warn(f"{manifest.name} no pasa la validación de Frameback ({'; '.join(problems)}); corrígelo (fecha de la "
             "carpeta, <topico>_<situacion>, ids de pieza de references/nombres.md)")


def read_manifest(project: Path) -> tuple[Path | None, dict]:
    manifest = next((project / m for m in MANIFESTS if (project / m).is_file()), None)
    if not manifest:
        return None, {}
    try:
        data = json.loads(manifest.read_text())
    except (ValueError, OSError):
        return manifest, {}  # invalid manifest: Frameback treats it as no template; defaults still apply
    return manifest, data if isinstance(data, dict) else {}


def project_layout(manifest: Path | None, data: dict) -> dict:
    layout = dict(DEFAULT_LAYOUT)
    if manifest and data:
        check_manifest(manifest, data)
        raw = data.get("layout") if isinstance(data.get("layout"), dict) else {}
        for k in DEFAULT_LAYOUT:
            v = raw.get(k)
            if isinstance(v, str) and v and not v.startswith("/") and ".." not in v.split("/"):
                layout[k] = v
    if layout["previous"].startswith(layout["deliveries"] + "/"):  # pre BL-090 manifest value
        layout["previous"] = layout["previous"][len(layout["deliveries"]) + 1:]
    return layout


def check_piece_declared(manifest: Path | None, data: dict, piece: str) -> None:
    """Warn (never write) when the delivered piece is not declared in `pieces` (PROTOCOL §9.1: optional, ordered)."""
    if not manifest or not data:
        return
    pieces = data.get("pieces")
    if not isinstance(pieces, list):
        warn(f'{manifest.name} no declara `pieces`; agrega [{{"id": "{piece}"}}, …] en el orden de las piezas del '
             "proyecto (mientras tanto Frameback las deduce de los nombres)")
    elif piece not in [p.get("id") for p in pieces if isinstance(p, dict)]:
        warn(f'la pieza {piece!r} no está en `pieces` de {manifest.name}; agrégala ({{"id": "{piece}"}}) en su '
             "lugar del orden declarado")


def fail(msg: str) -> None:
    print(f"deliver: {msg}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("new", type=Path, help="the new version, already in entregas/<piece>/")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, move nothing")
    ap.add_argument("--no-review-check", action="store_true",
                    help="archive even if the old version has a Frameback review and the new one does not")
    a = ap.parse_args()

    new = a.new.absolute()
    if new.is_symlink() or not new.is_file():
        fail(f"not a regular file: {a.new}")
    me = parse(new.name)
    if not me:
        fail(f"{new.name} does not follow references/nombres.md (needs …_vNN.<ext>)")
    piece = me["piece"]
    deliveries = new.parent  # the piece folder entregas/<piece>/ (entregas/ itself in the flat 0.4.x layout)
    # the project is the nearest folder with a manifest (a custom layout may nest entregas/)
    project = next((d for d in list(deliveries.parents)[:4] if any((d / m).is_file() for m in MANIFESTS)), None)
    if project is None:  # no manifest: entregas/<piece>/<file>, or the flat entregas/<file>
        project = deliveries.parent.parent if deliveries.name == piece else deliveries.parent
    manifest, data = read_manifest(project)
    layout = project_layout(manifest, data)
    proj = project.resolve()
    root = (project / layout["deliveries"]).resolve()
    here = deliveries.resolve()
    if here == root / piece:
        flat = False
    elif here == root:
        flat = True
    elif here.parent == root:
        fail(f"{a.new} is in {layout['deliveries']}/{deliveries.name}/ but its piece is {piece!r}: move it to "
             f"{layout['deliveries']}/{piece}/ (one folder per piece; folders that are not pieces are never touched)")
    else:
        fail(f"{a.new} is not directly in its piece folder ({layout['deliveries']}/{piece}/)")
    here_rel = here.relative_to(proj).as_posix()
    prev_rel = f"{here_rel}/{layout['previous']}"
    prev_dir = project / prev_rel
    final_dir = (project / layout["final"]).resolve()
    for p in (deliveries, prev_dir):
        r = p.resolve() if p.exists() else p.absolute()
        if r == final_dir or final_dir in r.parents or any(s in FORBIDDEN for s in r.parts):
            fail(f"refusing to write in {p} (final/ and .frameback/ belong to Frameback)")
    if flat:
        warn(f"layout plano 0.4.x ({layout['deliveries']}/<archivo>): se archiva en {prev_rel}/ como siempre, sin "
             f"migrar. Pasarlo a {layout['deliveries']}/<pieza>/ lo decide el creador y se hace a mano (Frameback lo "
             "sigue leyendo; `frameback adopt` no migra un proyecto ya adoptado, solo avisa `flat_layout`)")
    else:
        check_piece_declared(manifest, data, piece)

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
        print(f"deliver: nothing to archive; {new.name} is the only version in {here_rel}/")
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
                     f"(frameback open {here_rel}/{new.name}) so comments carry over, or pass --no-review-check")
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
        fail(f"{prev_rel}/ is on another volume; nothing moved")

    for src, dst in moves:
        print(f"{'would move' if a.dry_run else 'move'}: {src.relative_to(project)} -> {dst.relative_to(project)}")
        if a.dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():  # raced in after the check
            fail(f"destination appeared, stopped: {dst.relative_to(project)}")
        os.rename(src, dst)
    if not a.dry_run:
        print(f"deliver: current = {here_rel}/{new.name}; archived {len(stems)} version(s) in {prev_rel}/")


if __name__ == "__main__":
    main()
