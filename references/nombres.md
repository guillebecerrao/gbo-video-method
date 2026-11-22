# Convención de nombres

Decidida por el creador (2026-11-22) para que Frameback encuentre proyectos y versiones sin adivinar. Es convención
de archivos: sin Frameback instalado no cambia nada del flujo. La regex normativa vive en Frameback (`project.ts`,
`parseAssetName`); la de abajo la replica para poder comprobar nombres. Si alguna vez difieren, manda la de Frameback.

## Carpeta de proyecto

`AAAA-MM-DD_topico_situacion/`
- **Fecha de grabación** (no de edición ni de publicación).
- **Tópico amplio**, pocos y estables: `ia`, `marca-personal`, `builderia`…
- **Situación**: 2–4 palabras de qué pasó o de qué trata: `charla-agentes`, `ministra-ciencia-evento`.
- Ej.: `2026-11-20_ia_charla-agentes/`

## Archivos

```
<topico>_<situacion>_<formato>[_<artefacto>][_<variante>]_<vNN|final>.<ext>
```
- **Sin fecha** (la fecha ya está en la carpeta).
- **Partes**: minúsculas, sin tildes ni ñ; `-` dentro de cada parte, `_` solo entre partes.
- **formato** ∈ `reel` | `yt` | `feed`. Varias piezas del mismo formato: `<formato>-<N>-<slug>`, con número **y**
  slug (`reel-2-backstage`; `reel-2` solo es inválido). La primera pieza puede ir sin sufijo (`reel`).
- **artefacto** (opcional; sin él, es el video): `cover-9x16` | `cover-4x5` | `thumb-16x9` | `post`. Su contador
  propio se define aparte; mientras tanto siguen la regla de **Versionado de entregables** de `SKILL.md`.
- **variante** (opcional): una letra `a`–`z`, justo antes de la versión. Las variantes de una ronda comparten `vNN`.
- **versión**: `v` + dos dígitos (`v01`, `v02`…; `v100` en adelante permitido). **`_final` lo escribe Frameback** al
  aprobar (copia); gbo-video nunca crea un `_final`.
- **Sidecars** con el mismo stem que su video: `.srt`, `.timeline.json`, `.script.json`.

Ejemplos válidos:
```
ia_charla-agentes_reel_v01.mp4
ia_charla-agentes_reel_v01.srt
ia_charla-agentes_reel_v01.timeline.json
ia_charla-agentes_yt_v03.mp4
ia_charla-agentes_yt_thumb-16x9_v01.png
ia_charla-agentes_reel_cover-9x16_b_v02.jpg
ia_ministra-ciencia-evento_reel-2-backstage_v01.mp4
marca-personal_rutina-manana_feed_post_v01.md
ia_charla-agentes_reel_final.mp4          # solo Frameback
```
Inválidos: `ia_charla-agentes_reel-2_v01.mp4` (sin slug), `ia_charla-agentes_reel_v3.mp4` (un dígito),
`IA_Charla_reel_v01.mp4` (mayúsculas), `ia_tecnología_reel_v01.mp4` (tilde), `2026-11-20_ia_charla_reel_v01.mp4`
(fecha en el archivo), `ia_charla_youtube_v01.mp4` (formato fuera de la lista).

## Regex comprobable

```
PARTE    = [a-z0-9]+(-[a-z0-9]+)*
carpeta  = ^[0-9]{4}-[0-9]{2}-[0-9]{2}_PARTE_PARTE$
archivo  = ^PARTE_PARTE_(reel|yt|feed)(-[0-9]+-PARTE)?(_(cover-9x16|cover-4x5|thumb-16x9|post))?(_[a-z])?_(v([0-9]{2}|[1-9][0-9]{2,})|final)\.[a-z0-9]+(\.[a-z0-9]+)?$
```

## Proyectos existentes

Los proyectos en curso (p. ej. el de la ministra o HelloWorld) **conservan sus nombres hasta terminar**: no migrar en
caliente (rompe revisiones abiertas y rutas que el creador ya tiene). Los ya publicados no se migran. La convención
aplica a proyectos nuevos.
