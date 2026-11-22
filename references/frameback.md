# Revisión con Frameback (opcional)

[Frameback](https://github.com/guillebecerrao/frameback) es una interfaz local de revisión (`npx frameback`): el creador abre el video entregado, marca segundos,
rangos, regiones del cuadro o entidades del timeline (cortes, transiciones, B-roll, captions, palabras) y deja
comentarios que llegan **uno a uno** a esta sesión mientras sigue revisando. **Es una capa encima de esta skill, no un
requisito:** si no está disponible, los checkpoints ⏸ funcionan exactamente igual que siempre (feedback por chat).

- **Detección** (una vez por sesión): `command -v frameback`. Si no está, no insistir ni instalar nada sin que
  el creador lo pida; seguir el flujo estándar. (Instalación: `npm install -g frameback`; para desarrollarlo, `npm link` en el clon.)
  Los comentarios generales (abajo) y `check-name` (QA, `references/nombres.md`) requieren una versión con soporte de
  PROTOCOL §3.1 (posterior a 0.1.2): ver `frameback --version` / `frameback help | grep check-name`; para actualizar,
  `npm install -g frameback@latest` cuando esa versión esté publicada, o `npm link` en un clon de `main`. Con una
  versión anterior todo lo demás funciona igual; solo no se ven esos comentarios en `list`/`show`/MCP.
- **Cuándo:** al entregar un preview (⏸ fase 6) o un final (⏸ fase 8), si el creador pide revisar con Frameback o ya lo
  usa en el proyecto (existe `entregas/<pieza>/review/`, o `edit/review/` en proyectos anteriores a la plantilla).
- **Rutas:** en proyectos con la plantilla (`proyecto.json`, ver SKILL.md § Estructura de carpeta por video) el video
  entregado vive en la carpeta de su pieza, `entregas/<pieza>/`, y su revisión en `entregas/<pieza>/review/<stem>/`
  (PROTOCOL §1 y §9.2: la revisión va junto al video); las versiones previas, con su revisión, en
  `entregas/<pieza>/anteriores/` (y `anteriores/review/<stem>/`). En proyectos anteriores a la plantilla, lo mismo
  bajo `edit/` (y `edit/_reemplazados/` en vez de `anteriores/`); en proyectos 0.4.x con layout plano, `entregas/` y
  `entregas/anteriores/` sin carpeta de pieza. No migrar ninguno en caliente. Nunca escribir en `final/` ni en
  `.frameback/`: son de Frameback (al aprobar copia a `final/<pieza>/`).
- **Arranque:** `frameback open entregas/<pieza>/<base>_vNN.mp4` (`<base>` = `<topico>_<situacion>_<pieza>`, ver `references/nombres.md`) en segundo plano (imprime la URL y la carpeta de revisión
  `entregas/<pieza>/review/<base>_vNN/`), y `frameback watch entregas/<pieza>/<base>_vNN.mp4 --json --actor human,system` con la
  herramienta **Monitor** (una notificación por comentario del creador, sin los ecos de lo que escribe el agente). `gbo_render.py` deja junto al render un `<salida>.timeline.json` que Frameback
  usa para mostrar cortes, cambios de speaker, B-roll, punch-ins y captions con tiempos exactos (`--no-timeline` lo
  desactiva). Si no hay sidecar, Frameback lee `edit/edl.json` (tiempos aproximados).
- **Mientras el creador revisa: adelantar todo lo posible, apenas llega cada comentario.** Nunca esperar a
  `review.submitted` para empezar (y no usar `watch --exit-on review.submitted` como alternativa: eso rompe el flujo).
  El orquestador de la edición **no hace el trabajo pesado**: atiende el aviso, mira el snapshot
  (`snapshots/<id>.jpg`), clasifica y reparte; así queda libre para el comentario siguiente.
  1. *Ajuste puntual* (cambiar un punto de corte, sacar un B-roll, corregir un caption o el glosario, ajustar un
     punch-in) → `frameback update <dir> <id> --status in_progress`, aplicar el cambio sobre **`edit/edl.next.json`**
     (copia de staging del EDL; nunca tocar el entregable) y `--status prepared --plan "…"`.
  2. *Requiere producir algo* (otra foto o B-roll, otra canción, rediseñar una animación o tarjeta, un SFX, un regrade)
     → `--status in_progress` con el plan y **lanzar un subagente en segundo plano** que lo deje listo en staging:
     asset en `edit/staging/<id>/` (o componente/props de Remotion con un still de prueba) y la entrada que usaría en
     `edl.next.json`. Al terminar, el orquestador revisa el resultado y marca `--status prepared --plan "…"`. Varios
     subagentes pueden correr en paralelo si no tocan lo mismo; dos comentarios sobre el mismo tramo, uno solo.
  3. *Decisión del creador o ambiguo* (re-estructurar el corte, cambiar el hook, gusto no claro) →
     `--status needs_info` + `frameback reply <dir> <id> "pregunta concreta"` (con opciones si ayuda). No adivinar;
     cuando responda, pasa a 1 o 2.
  **Comentarios generales** (`anchor.scope: "video"`, PROTOCOL §3.1): notas sobre la pieza entera («el ritmo se
  arrastra», «la música está alta en todo el video»). Se reconocen así, en el evento de `watch --json` (`data` de
  `comment.created` / `comment.updated` / `comment.carried`) o en `list`/`show --json`:
  - `scope: "video"` y sin `time` → **general**: no hay cuadro, rango, región, entidad ni snapshot que mirar; el
    cambio aplica a todo el corte (p. ej. bajar la música en toda la mezcla, apretar el aire de todos los cortes).
  - con `time` → **anclado a tiempo** (puede traer además `target`); `scope` `null` o ausente.
  - sin `time` y con `target` → **anclado al guion** (sección, decisión…; ver § Guion en Frameback); `scope` `null` o ausente.
  Se atienden con el mismo flujo de estados, `--plan` y `reply` que cualquier otro (pasos 1–3); como no señalan un
  punto concreto, ante la duda de dónde o cuánto aplica, `needs_info` con opciones antes que adivinar. Un `PATCH` del
  creador puede volverlo anclado a tiempo (o al revés): llega como `comment.updated` y se re-planifica. En la versión
  siguiente siempre se traspasa con su anchor (nunca queda `lost`). Requiere Frameback con §3.1: la interfaz del 0.1.2 no
  permite crearlos y, si otro Frameback los creó, su `watch --json` transmite el evento (sin `time`) pero su
  `list`/MCP los salta y `show` falla en ese comentario.
  Comentario editado (`revision` > `seenRevision`) → re-planificar (y cancelar el subagente si quedó obsoleto);
  comentario borrado → deshacer lo preparado. Las decisiones de juicio editorial siguen la regla de **Modelo por fase**.
- **Al pulsar "Procesar" (`review.submitted`) — el botón del creador gatilla el entregable:** solo se integra lo ya
  preparado; nada se empieza de cero aquí. Esperar a los subagentes que sigan corriendo, `frameback review <dir>
  --state processing`; promover `edl.next.json` → `edl.json` (con los assets de `edit/staging/`) y renderizar **una
  sola vez** la versión siguiente según
  **Versionado de entregables** (`-o entregas/<pieza>/<base>_v<NN+1>.mp4`; la anterior se archiva al final); marcar cada comentario
  `--status applied --applied-in <base>_v<NN+1>` (o `declined` con razón); `frameback review <dir> --state delivered
  --next-video entregas/<pieza>/<base>_v<NN+1>.mp4` y abrir la nueva versión (`frameback open …`): los comentarios se traspasan
  solos para que el creador verifique. **Detener el watch anterior e iniciar uno nuevo sobre `_v<NN+1>`**: los
  comentarios que el creador reabra ahí vuelven a `pending` y son la siguiente ronda. **Recién después de abrir la
  nueva** (el traspaso de comentarios y el campo `previous` se resuelven buscando la revisión anterior junto a la
  nueva, en `entregas/<pieza>/review/`), archivar la anterior: `python3 edit/deliver.py
  entregas/<pieza>/<base>_v<NN+1>.mp4` mueve `<base>_vNN.*` (video + sidecars) y `entregas/<pieza>/review/<base>_vNN/`
  juntos a `entregas/<pieza>/anteriores/`. Así la revisión vieja sigue reproduciendo su video desde `anteriores/`, y
  Frameback re-resuelve el enlace `next` por nombre dentro de las carpetas de la pieza. `deliver.py` se niega si la
  nueva aún no tiene revisión o si el archivo no está en la carpeta de su pieza.
- **Retro (fase 9):** los comentarios de Frameback son la mejor fuente de aprendizajes: `frameback export <dir>`
  genera un resumen en Markdown para proponer reglas en `<perfil>/aprendizajes.md`.
- **Estados de la revisión:** `delivered` y `closed` se aplican solo a la revisión de la versión **reemplazada**
  (`_vNN`), nunca a la recién abierta (`_v<NN+1>`), que debe quedar en `reviewing`; si no, Frameback bloquea los
  comentarios nuevos y el clic en planos solo mueve el cabezal. Nada de `--force` en estados sin pedido explícito. Si
  se bloqueó por error, el creador puede pulsar **Reopen review** en el panel de comentarios.


## Guion en Frameback (`<stem>.script.json`)

Frameback muestra el **guion del productor** junto al video (secciones, propósito, texto, directrices, decisiones,
animaciones, indicaciones) si existe `<stem>.script.json` junto al render (contrato: `PROTOCOL.md` §8 de Frameback).
Sin él, Frameback arma un guion automático desde el timeline.

- **Fuente:** `edit/guion.json`, guion estructurado propio de gbo-video (plantilla `templates/guion.ejemplo.json`). Se
  arma desde el guion aprobado (`guion.md` / `guion_snapshot.md`) al pasar a edición y es la fuente de verdad del
  guion **en edición**: los cambios de la revisión se escriben aquí, nunca en el sidecar ni en la copia congelada.
  - `sections[]`: `id` estable (obligatorio, `^[a-z0-9][a-z0-9._-]{0,63}$`, prefijo `s-`), `title`, `purpose`,
    `text`, y su ubicación: `beats` (los `beat` de los tramos del EDL; en reels, el `label` del segmento) **o**
    `ranges` explícitos en segundos del video final (`[[inicio, fin]]` o `[{start, end}]`). `omitted: true` = escrita
    pero cortada; una sección con `beats` que no calzan con ningún corte queda `omitted` sola.
  - `guidelines` (`g-`), `decisions` (`d-`: `status` proposed | active | superseded | rejected, `origin`, `since`,
    `supersedes`), `animations` (`a-`: `kind`, `label`, `start`/`end` en tiempo final, o `beat` + `offset` + `dur`),
    `directions` (`r-`: `kind` recording | editing). `section` opcional (null = global). Ids únicos en todo el guion
    y **los mismos entre versiones**: Frameback traslada los comentarios por id.
  - `original` (opcional): el guion previo a grabar, mismo formato, para comparar (sus tiempos se ignoran).
- **Generación:** `gbo_render.py` y `reel_render.py` llaman a `scripts/script_sidecar.py` al terminar (`--no-script`
  lo desactiva; a mano: `python3 edit/script_sidecar.py entregas/<pieza>/<base>_vNN.mp4`, que encuentra
  `<proyecto>/edit/guion.json` desde `entregas/<pieza>/`, su `anteriores/` o el `entregas/` plano). Resuelve los rangos contra el
  `.timeline.json` del render (sin timeline, desde el EDL, aproximado), ordena las secciones como aparecen en el
  video, pone `version` = el `NN` del nombre, `scriptId` = el nombre sin `_vNN`, `source: prewritten`, `producer`
  y `video.hash`/`duration` (Frameback marca el guion `ok` solo si el hash calza con el video abierto). Sin
  `edit/guion.json` no hace nada; si falla, avisa y el render sigue (mismo exit code). Validar a mano:
  `frameback script --check entregas/<pieza>/<base>_vNN.script.json`.
- **Llevar las decisiones de la revisión a vN+1** (en `edit/guion.json`, antes de renderizar la versión siguiente;
  `since` = número de la versión nueva, `origin.review` = stem de la revisión de vN, `origin.comment` = id `c-NNNN`):
  - *Comentario aceptado que fija un criterio* → decisión nueva `status: active`, `origin {review, comment}`, `since`.
  - *Propuesta aceptada* (`human.acceptedProposal` en el comentario, evento `comment.proposal_accepted`) → aplicar el
    cambio de texto (`proposal.after` en lugar de `proposal.before`, en el campo de `proposal.target`) **y** agregar
    la decisión `active` con `origin` y `since`. Una propuesta no aceptada no se aplica sola.
  - *Revertir una decisión* → la anterior pasa a `superseded` y la nueva lleva `supersedes: <id anterior>`.
  - *Declinado* → comentario `declined` con razón; opcional, una decisión `rejected` con `origin` para que no vuelva.
  - Nunca cambiar ni reutilizar los ids existentes; las decisiones viejas se conservan con su estado.
