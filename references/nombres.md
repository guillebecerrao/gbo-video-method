# Convención de nombres

Decidida por el creador (2026-11-22) para que Frameback encuentre proyectos y versiones sin adivinar. Es convención
de archivos: sin Frameback instalado no cambia nada del flujo. La norma es Frameback `docs/PROTOCOL.md` §9.3
(`ASSET_NAME_RE` / `parseAssetName` en `src/core/project.ts`); la regex de abajo la replica para poder comprobar
nombres. Si alguna vez difieren, **manda §9.3**.

## Carpeta de proyecto

`AAAA-MM-DD_topico_situacion/`
- **Fecha de grabación** (no de edición ni de publicación). Si aún no se graba, la prevista. Si la grabación cambia
  de día, se renombra la carpeta al ingerir el material, **solo antes de la primera entrega**; después no se toca.
- **Tópico amplio**, pocos y estables: `ia`, `marca-personal`, `builderia`…
- **Situación**: 2–4 palabras de qué pasó o de qué trata: `charla-agentes`, `ministra-ciencia-evento`.
- Ej.: `2026-11-20_ia_charla-agentes/`

## Carpeta de pieza

Cada archivo entregado vive en la carpeta de **su pieza**: `entregas/<pieza>/`, donde `<pieza>` es la parte de pieza
del nombre (`reel`, `yt`, `feed` o `<formato>-<N>-<slug>`). **Siempre**, también cuando el proyecto tiene una sola pieza
(`entregas/reel/`). Sus versiones previas, en `entregas/<pieza>/anteriores/`; lo aprobado lo copia Frameback a
`final/<pieza>/` (PROTOCOL §9.2). Un archivo de otra pieza dentro de una carpeta de pieza Frameback lo lista como sin
clasificar; los sueltos en `entregas/` solo se leen como legado del layout plano de 0.4.x. Las piezas se declaran en `proyecto.json` (`pieces: [{"id": …}]`, en el orden
del proyecto). Ej.: `entregas/yt/ia_charla_yt_v03.mp4`, `entregas/reel-1-hook/ia_charla_reel-1-hook_cover-9x16_b_v01.jpg`.

## Archivos

```
<topico>_<situacion>_<formato>[_<artefacto>][_<variante>]_<vNN|final>.<ext>
```
- **Sin fecha** (la fecha ya está en la carpeta).
- **Partes**: minúsculas, sin tildes ni ñ; `-` dentro de cada parte, `_` solo entre partes.
- **formato** ∈ `reel` | `yt` | `feed`. Una sola pieza de ese formato: `reel` a secas. Varias piezas del mismo
  formato: **todas**, también la primera, llevan `<formato>-<N>-<slug>`, con número **y** slug, numeradas desde 1
  (`reel-1-hook`, `reel-2-backstage`). `reel-2` sin slug y `reel-0-x` son inválidos.
- **artefacto** (opcional; sin él, es el video): `cover-9x16` | `cover-4x5` | `thumb-16x9` | `post`. Su contador
  propio se define aparte; mientras tanto siguen la regla de **Versionado de entregables** de `SKILL.md`.
- **variante** (opcional): una letra `a`–`z`, justo antes de la versión. Las variantes de una ronda comparten `vNN`.
- **versión**: `v` + dos dígitos (`v01`, `v02`…; `v100` en adelante permitido). **`_final` lo escribe Frameback** al
  aprobar (copia); gbo-video nunca crea un `_final`. El final **no lleva la letra de variante**: aprobar
  `…_cover-9x16_b_v02.jpg` da `…_cover-9x16_final.jpg` (nunca `_<letra>_final`).
- **Extensión** siempre en minúsculas (`.mp4`, no `.MP4`).
- **Sidecars** con el mismo stem que su video: `.srt`, `.timeline.json`, `.script.json`.

Ejemplos válidos:
```
ia_charla-agentes_reel_v01.mp4
ia_charla-agentes_reel_v01.srt
ia_charla-agentes_reel_v01.timeline.json
ia_charla-agentes_yt_v03.mp4
ia_charla-agentes_yt_thumb-16x9_v01.png
ia_charla-agentes_reel_cover-9x16_b_v02.jpg
ia_ministra-ciencia-evento_reel-1-discurso_v01.mp4
ia_ministra-ciencia-evento_reel-2-backstage_v01.mp4
marca-personal_rutina-manana_feed_post_v01.md
ia_charla-agentes_reel_final.mp4          # solo Frameback
ia_charla-agentes_reel_cover-9x16_final.jpg   # solo Frameback (aprobada la variante b)
```
Inválidos: `ia_charla-agentes_reel-2_v01.mp4` (sin slug), `ia_charla-agentes_reel_v3.mp4` (un dígito),
`IA_Charla_reel_v01.mp4` (mayúsculas), `ia_tecnología_reel_v01.mp4` (tilde), `2026-11-20_ia_charla_reel_v01.mp4`
(fecha en el archivo), `ia_charla_youtube_v01.mp4` (formato fuera de la lista), `ia_charla-agentes_reel-0-hook_v01.mp4`
(número 0), `ia_charla-agentes_reel_v01.MP4` (extensión en mayúsculas), `ia_charla-agentes_reel_cover-9x16_b_final.jpg`
(final con letra de variante).

## Regex comprobable

Réplica de `ASSET_NAME_RE` (§9.3). La regex sola no rechaza `_<letra>_final`: esa regla es de esta convención.

```
PARTE    = [a-z0-9]+(-[a-z0-9]+)*
carpeta  = ^[0-9]{4}-[0-9]{2}-[0-9]{2}_PARTE_PARTE$
archivo  = ^PARTE_PARTE_(reel|yt|feed)(-[1-9][0-9]*-PARTE)?(_(cover-9x16|cover-4x5|thumb-16x9|post))?(_[a-z])?_(v[0-9]{2,}|final)\.[a-z0-9]+(\.[a-z0-9]+)*$
```

## Comprobar antes de entregar (QA, fase 8)

Antes de avisar una entrega, comprobar los nombres de lo que queda en las carpetas de pieza `entregas/<pieza>/`, y que
cada archivo esté en la carpeta de su pieza (la parte de pieza de su nombre = el nombre de la carpeta). **Manda el
validador de Frameback**; la regex de arriba es la referencia solo cuando no está.

- **Con Frameback** (`command -v frameback`) **y** una versión que tenga el comando (`frameback help | grep -q
  check-name`; el 0.1.x publicado no lo trae y responde `unknown command` con exit 1, que no hay que leer como
  «nombre inválido»):

  ```
  find entregas -mindepth 2 -maxdepth 2 -type f ! -name '.*' \( -path 'entregas/reel*' -o -path 'entregas/yt*' -o -path 'entregas/feed*' \) -exec frameback check-name {} +
  ```

  Solo los archivos sueltos de cada carpeta de pieza: un glob como `entregas/*/*` también recibiría las carpetas
  `anteriores/` y `review/` (las marcaría `fail`, `no_extension`) y los archivos de carpetas que no son pieza
  (`entregas/muestras/`), que no siguen la convención ni hay que tocar. Lee solo el nombre base (los archivos no
  necesitan existir), así que no ve la carpeta: que cada archivo esté en `entregas/<su pieza>/` se mira aparte
  (`deliver.py` se niega a entregar uno fuera de su carpeta). En un proyecto que sigue en el layout plano de 0.4.x
  (archivos sueltos en `entregas/`), el mismo comando con `find entregas -maxdepth 1 -type f ! -name '.*' …`.
  Exit `0` = todos válidos; `1` = alguno inválido (cada `fail` trae `code: reason`, p. ej. `bad_version: version 'v3'
  needs two digits (e.g. v03)`); `2` = error de uso. Con `--json` imprime `[{name, ok, parsed?, code?, reason?}]`.
  Corregir cada nombre que falle (renombrar el archivo **y sus sidecars** con el mismo stem) y volver a correrlo hasta
  exit 0. Si el archivo ya se abrió en Frameback, renombrarlo deja huérfana su revisión: preguntar al creador antes.
- **Sin Frameback** (o sin `check-name`): comprobar con la regex de § Regex comprobable (más la regla de
  `_<letra>_final`). Nada más cambia en el flujo.
- **Proyectos sin `proyecto.json`** (anteriores a la plantilla) se saltan este paso: conservan sus nombres.

## Proyectos existentes

Los proyectos en curso (p. ej. el de la ministra o HelloWorld) **conservan sus nombres hasta terminar**: no migrar en
caliente (rompe revisiones abiertas y rutas que el creador ya tiene). Los ya publicados no se migran. La convención
aplica a proyectos nuevos.
