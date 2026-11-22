"""Sidecar de guion `<stem>.script.json` para Frameback (PROTOCOL §8), desde `edit/guion.json`.

    python edit/script_sidecar.py entregas/ia_charla-agentes_reel_v04.mp4          # busca edit/guion.json del proyecto
    python edit/script_sidecar.py entregas/ia_charla-agentes_reel_v04.mp4 --guion edit/guion.json --timeline entregas/ia_charla-agentes_reel_v04.timeline.json

`gbo_render.py` y `reel_render.py` lo llaman solos al terminar (`--no-script` lo desactiva). Sin `guion.json` no hace
nada. Es opcional y aditivo: el render nunca depende de él, y el sidecar no hace daño sin Frameback.

Qué resuelve contra el render (formato de `guion.json` en `templates/guion.ejemplo.json`):
  - rangos en segundos del video FINAL: `ranges` explícitos de la sección, o la unión de los cortes cuyo `beat`
    (`meta.beat` del `.timeline.json`; en reels, el `label` del segmento) está en `beats`; sin timeline, desde los
    `ranges` + `beat` del `edl.json` (tiempos aproximados). Una sección con `beats` que no calzan con ningún corte
    queda `omitted: true` (escrita, pero no está en este corte)
  - animaciones con `start`/`end` o ancladas a un beat (`beat` + `offset` + `dur`)
  - secciones en orden del video; ids estables (los de `guion.json`, nunca generados)
  - `version` = número del render (`_vNN` del nombre), `scriptId` = nombre sin `_vNN` (saneado a
    `^[a-z0-9][a-z0-9._-]{0,63}$`), `video.hash` (sha1 de los primeros + últimos 64 KB, el mismo algoritmo que
    `video.fingerprint.hash` de Frameback) y `video.duration`

Solo stdlib (ffprobe opcional, para la duración).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
COMMENT_RE = re.compile(r"^c-\d{4,}$")
VERSION_RE = re.compile(r"^(?P<base>.*?)[_.-]v(?P<n>\d+)$", re.IGNORECASE)
DECISION_STATUSES = {"proposed", "active", "superseded", "rejected"}
DIRECTION_KINDS = {"recording", "editing"}
CHUNK = 64 * 1024
EPS = 1e-3


# ------------------------------------------------------------- identity ----

def video_hash(path: Path) -> str:
    """sha1 hex of the first 64 KB + the last 64 KB (from max(64 KB, size - 64 KB)): Frameback's fingerprint."""
    h = hashlib.sha1()
    with open(path, "rb") as f:
        size = f.seek(0, 2)
        f.seek(0)
        h.update(f.read(CHUNK))
        if size > CHUNK:
            f.seek(max(CHUNK, size - CHUNK))
            h.update(f.read(CHUNK))
    return h.hexdigest()


def sanitize_id(s: str) -> str:
    """Lowercase ASCII slug matching ^[a-z0-9][a-z0-9._-]{0,63}$ (accents dropped, other chars → '-')."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"^[^a-z0-9]+", "", s)[:64].rstrip("-") or "video"
    return s


def stem_identity(stem: str) -> tuple[str, int | None]:
    """`ia_charla-agentes_reel_v04` → ('ia_charla-agentes_reel', 4); without `_vNN` → (stem, None)."""
    m = VERSION_RE.match(stem)
    if m and m.group("base"):
        return sanitize_id(m.group("base")), int(m.group("n"))
    return sanitize_id(stem), None


def producer_version() -> str | None:
    """Skill version from the first released heading of CHANGELOG.md (scripts may run from a copy in edit/)."""
    for root in (Path(__file__).resolve().parent.parent, Path.home() / ".claude/skills/gbo-video"):
        cl = root / "CHANGELOG.md"
        if cl.is_file():
            m = re.search(r"^## (\d+\.\d+\.\d+)", cl.read_text(encoding="utf-8"), re.M)
            if m:
                return m.group(1)
    return None


def probe_duration(path: Path) -> float | None:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            str(path)], capture_output=True, text=True, timeout=30)
        return round(float(r.stdout.strip()), 3)
    except Exception:
        return None


# ------------------------------------------------------------- timeline ----

def cuts_from_timeline(timeline: dict) -> list[dict]:
    """[{start, end, beat}] from the `cuts` track (else the first track with `range` items)."""
    tracks = timeline.get("tracks", [])
    track = next((t for t in tracks if t.get("id") == "cuts"), None) or \
        next((t for t in tracks if any(i.get("type") == "range" for i in t.get("items", []))), None)
    out = []
    for it in (track or {}).get("items", []):
        meta = it.get("meta") or {}
        if "beat" in meta:
            beat = meta.get("beat") or ""
        else:   # reel_render: no meta.beat; the label is "<segment label> · <src> <in>–<out>"
            beat = str(it.get("label", "")).rsplit(" · ", 1)[0]
        out.append({"start": float(it["start"]), "end": float(it["end"]), "beat": beat.strip()})
    return out


def cuts_from_edl(edl: dict) -> list[dict]:
    """Approximate output times from a gbo_render EDL (`ranges` with `beat`, cumulative, speed-aware)."""
    out, t = [], 0.0
    for r in edl.get("ranges", []):
        d = (float(r["end"]) - float(r["start"])) / float(r.get("speed", 1.0))
        out.append({"start": round(t, 3), "end": round(t + d, 3), "beat": str(r.get("beat", "")).strip()})
        t += d
    return out


def ranges_for_beats(beats: list[str], cuts: list[dict]) -> list[dict]:
    """Union of the cuts whose beat is in `beats` (case-insensitive), contiguous cuts merged, in time order."""
    want = {b.strip().lower() for b in beats}
    spans = sorted((c["start"], c["end"]) for c in cuts if c["beat"].lower() in want and c["end"] > c["start"])
    merged: list[list[float]] = []
    for a, b in spans:
        if merged and a <= merged[-1][1] + EPS:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [{"start": round(a, 3), "end": round(b, 3)} for a, b in merged]


# ------------------------------------------------------------ guion.json ----

def _ranges(raw) -> list[dict]:
    """Explicit ranges: [{start, end}] or [[start, end]]."""
    out = []
    for r in raw:
        a, b = (r["start"], r["end"]) if isinstance(r, dict) else (r[0], r[1])
        out.append({"start": round(float(a), 3), "end": round(float(b), 3)})
    return sorted(out, key=lambda r: r["start"])


def _opt(d: dict, key: str):
    v = d.get(key)
    return v if v not in ("",) else None


def _content(g: dict, cuts: list[dict] | None, warn, placed: bool) -> dict:
    """Normalize the shared content (sections + four lists). `placed=False` for `original` (times ignored)."""
    sections, first_range = [], {}
    for s in g.get("sections", []):
        sec = {"id": s.get("id"), "title": s.get("title"), "purpose": _opt(s, "purpose"),
               "beats": s.get("beats") or None, "text": _opt(s, "text"), "omitted": bool(s.get("omitted", False))}
        if not placed:
            sec["ranges"] = []
        elif sec["omitted"]:
            sec["ranges"] = []
        elif s.get("ranges") is not None:
            sec["ranges"] = _ranges(s["ranges"])
        elif sec["beats"] and cuts is not None:
            sec["ranges"] = ranges_for_beats(sec["beats"], cuts)
            if not sec["ranges"]:
                sec["omitted"] = True
                warn(f'sección "{sec["id"]}": ningún corte con beat {sec["beats"]}; queda omitted')
        else:
            if sec["beats"]:
                warn(f'sección "{sec["id"]}": sin timeline ni EDL para resolver sus beats; queda sin ubicar')
            sec["ranges"] = []
        if sec["ranges"]:
            first_range[sec["id"]] = sec["ranges"][0]["start"]
        sections.append(sec)

    # video order: by first placed range; unplaced sections stay right after their predecessor (Frameback's rule)
    prev, keyed = float("-inf"), []
    for idx, sec in enumerate(sections):
        if sec["ranges"]:
            prev = sec["ranges"][0]["start"]
        keyed.append((prev, idx, sec))
    sections = [k[2] for k in sorted(keyed, key=lambda k: (k[0], k[1]))]

    sec_start = {s["id"]: s["ranges"][0]["start"] for s in sections if s["ranges"]}
    beat_start = {}
    for c in cuts or []:
        beat_start.setdefault(c["beat"].lower(), c["start"])

    animations = []
    for a in g.get("animations", []):
        start, end = a.get("start"), a.get("end")
        if start is None and placed:
            base = None
            if a.get("beat"):
                base = beat_start.get(str(a["beat"]).lower())
            elif a.get("section") in sec_start:
                base = sec_start[a["section"]]
            if base is None:
                warn(f'animación "{a.get("id")}": no se pudo ubicar en este corte; se omite')
                continue
            start = base + float(a.get("offset", 0))
            end = start + float(a["dur"]) if a.get("dur") is not None else None
        animations.append({"id": a.get("id"), "section": a.get("section"), "kind": a.get("kind", "other"),
                           "label": a.get("label"), "text": _opt(a, "text"),
                           "start": round(float(start or 0), 3),
                           "end": round(float(end), 3) if end is not None else None})

    return {
        "sections": sections,
        "guidelines": [{"id": x.get("id"), "section": x.get("section"), "text": x.get("text")}
                       for x in g.get("guidelines", [])],
        "decisions": [{"id": x.get("id"), "section": x.get("section"), "text": x.get("text"),
                       "status": x.get("status", "active"), "origin": x.get("origin"),
                       "since": x.get("since"), "supersedes": x.get("supersedes")}
                      for x in g.get("decisions", [])],
        "animations": animations,
        "directions": [{"id": x.get("id"), "section": x.get("section"), "kind": x.get("kind"),
                        "text": x.get("text")} for x in g.get("directions", [])],
    }


def validate(doc: dict, where: str = "") -> None:
    """The checks that would make Frameback ignore the sidecar: fail loudly here instead."""
    errs, seen = [], set()
    sections = {s["id"] for s in doc["sections"]}
    for lst in ("sections", "guidelines", "decisions", "animations", "directions"):
        for i, it in enumerate(doc[lst]):
            p = f"{where}{lst}[{i}]"
            if not isinstance(it.get("id"), str) or not ID_RE.match(it["id"]):
                errs.append(f"{p}.id {it.get('id')!r} debe cumplir ^[a-z0-9][a-z0-9._-]{{0,63}}$ (fijarlo en guion.json)")
            elif it["id"] in seen:
                errs.append(f"{p}.id {it['id']!r} repetido (los ids son únicos en todo el guion)")
            seen.add(it.get("id"))
            if lst != "sections" and it.get("section") is not None and it["section"] not in sections:
                errs.append(f"{p}.section {it['section']!r} no existe")
            need = "title" if lst == "sections" else ("label" if lst == "animations" else "text")
            if not (isinstance(it.get(need), str) and it[need].strip()):
                errs.append(f"{p}.{need} es obligatorio")
            if lst == "sections":
                for r in it["ranges"]:
                    if r["start"] < 0 or r["end"] <= r["start"]:
                        errs.append(f"{p}: rango inválido {r}")
            if lst == "decisions":
                if it["status"] not in DECISION_STATUSES:
                    errs.append(f"{p}.status {it['status']!r}: proposed | active | superseded | rejected")
                o = it.get("origin")
                if o is not None and not (isinstance(o, dict) and o.get("review") and COMMENT_RE.match(str(o.get("comment", "")))):
                    errs.append(f"{p}.origin debe ser {{review: <stem de la revisión>, comment: c-0000}}")
                if it.get("since") is not None and not (isinstance(it["since"], int) and it["since"] >= 1):
                    errs.append(f"{p}.since debe ser un entero >= 1")
                if it.get("supersedes") is not None and not ID_RE.match(str(it["supersedes"])):
                    errs.append(f"{p}.supersedes {it['supersedes']!r} no es un id válido")
            if lst == "directions" and it.get("kind") not in DIRECTION_KINDS:
                errs.append(f"{p}.kind {it.get('kind')!r}: recording | editing")
            if lst == "animations":
                if not re.match(r"^[a-z0-9_-]{1,40}$", str(it.get("kind"))):
                    errs.append(f"{p}.kind {it.get('kind')!r} debe ser un slug en minúsculas")
                if it["start"] < 0 or (it["end"] is not None and it["end"] < it["start"]):
                    errs.append(f"{p}: tiempos inválidos start={it['start']} end={it['end']}")
    if errs:
        raise ValueError("guion.json inválido:\n  " + "\n  ".join(errs[:20]))


# ------------------------------------------------------------------ main ----

def build(video: Path, guion: dict, cuts: list[dict] | None, version: int | None = None,
          duration: float | None = None, warn=None) -> dict:
    warn = warn or (lambda m: print(f"aviso (guion): {m}", file=sys.stderr))
    script_id, n = stem_identity(video.stem)
    if version is None:
        version = n
    if version is None:
        version = 1
        warn(f"{video.name} no termina en _vNN; se usa version 1")
    if not guion.get("title"):
        raise ValueError("guion.json inválido: falta title")
    doc = {
        "schemaVersion": 1,
        "kind": "frameback.script",
        "scriptId": script_id,
        "version": int(version),
        "source": "prewritten",
        "producer": {"name": "gbo-video", "version": producer_version()},
        "createdAt": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "video": {"file": video.name, "duration": duration, "hash": video_hash(video)},
        "title": guion["title"],
        "summary": _opt(guion, "summary"),
        **_content(guion, cuts, warn, placed=True),
        "original": None,
    }
    validate(doc)
    if guion.get("original"):
        o = guion["original"]
        orig = {"createdAt": o.get("createdAt"), "title": o.get("title") or guion["title"],
                "summary": _opt(o, "summary"), **_content(o, None, warn, placed=False)}
        validate(orig, "original.")
        doc["original"] = orig
    return doc


def write_script_sidecar(video: Path, edit_dir: Path, timeline: Path | None = None, edl: Path | None = None,
                         guion: Path | None = None, version: int | None = None) -> Path | None:
    """Write `<video stem>.script.json` next to the video. Returns None (and writes nothing) without guion.json.
    Raises on errors: callers (the renders) catch, warn and keep their exit code."""
    video = Path(video).resolve()
    gpath = Path(guion) if guion else Path(edit_dir) / "guion.json"
    if not gpath.is_file():
        return None
    g = json.loads(gpath.read_text(encoding="utf-8"))
    tl_path = Path(timeline) if timeline else video.with_suffix(".timeline.json")
    cuts, duration = None, None
    if tl_path.is_file():
        tl = json.loads(tl_path.read_text(encoding="utf-8"))
        cuts, duration = cuts_from_timeline(tl), tl.get("duration")
    elif edl and Path(edl).is_file():
        e = json.loads(Path(edl).read_text(encoding="utf-8"))
        if e.get("ranges"):
            cuts = cuts_from_edl(e)
            print("aviso (guion): sin .timeline.json; rangos aproximados desde el EDL", file=sys.stderr)
    duration = probe_duration(video) or duration
    doc = build(video, g, cuts, version=version, duration=duration)
    out = video.with_suffix(".script.json")
    data = json.dumps(doc, ensure_ascii=False, indent=1)
    if len(data.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("el sidecar supera 2 MB (Frameback lo ignoraría)")
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Escribe <stem>.script.json (Frameback §8) desde edit/guion.json.")
    ap.add_argument("video", type=Path, help="render entregado (entregas/<topico>_<situacion>_<formato>_vNN.mp4)")
    ap.add_argument("--guion", type=Path, help="guion estructurado (default: <proyecto>/edit/guion.json si el video está en entregas/, si no <carpeta del video>/guion.json)")
    ap.add_argument("--timeline", type=Path, help="default: <video>.timeline.json")
    ap.add_argument("--edl", type=Path, help="edl.json para ubicar beats si no hay timeline")
    ap.add_argument("--version", type=int, help="forzar version (default: el _vNN del nombre)")
    a = ap.parse_args()
    vdir = a.video.resolve().parent
    edit_dir = vdir.parent / "edit" if vdir.name == "entregas" and (vdir.parent / "edit").is_dir() else vdir
    out = write_script_sidecar(a.video, edit_dir, a.timeline, a.edl, a.guion, a.version)
    if out is None:
        print("sin guion.json: no se escribió sidecar de guion")
    else:
        print(f"guion → {out.name} (Frameback, opcional)")


if __name__ == "__main__":
    main()
