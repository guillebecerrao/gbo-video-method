# Revisión con Frameback (opcional)

[Frameback](https://github.com/guillebecerrao/frameback) es una interfaz local de revisión (`npx frameback`): el creador abre el video entregado, marca segundos,
rangos, regiones del cuadro o entidades del timeline (cortes, transiciones, B-roll, captions, palabras) y deja
comentarios que llegan **uno a uno** a esta sesión mientras sigue revisando. **Es una capa encima de esta skill, no un
requisito:** si no está disponible, los checkpoints ⏸ funcionan exactamente igual que siempre (feedback por chat).

- **Detección** (una vez por sesión): `command -v frameback`. Si no está, no insistir ni instalar nada sin que
  el creador lo pida; seguir el flujo estándar. (Instalación: `npm install -g frameback`; para desarrollarlo, `npm link` en el clon.)
- **Cuándo:** al entregar un preview (⏸ fase 6) o un final (⏸ fase 8), si el creador pide revisar con Frameback o ya lo
  usa en el proyecto (existe `entregas/review/`, o `edit/review/` en proyectos anteriores a la plantilla).
- **Rutas:** en proyectos con la plantilla (`proyecto.json`, ver SKILL.md § Estructura de carpeta por video) el video
  entregado vive en `entregas/` y su revisión en `entregas/review/<stem>/` (PROTOCOL §1: la revisión va junto al
  video). En proyectos anteriores a la plantilla, lo mismo bajo `edit/` (y `edit/_reemplazados/` en vez de
  `entregas/anteriores/`); no migrarlos. Nunca escribir en `final/` ni en `.frameback/`: son de Frameback.
- **Arranque:** `frameback open entregas/<base>_vNN.mp4` (`<base>` = `<topico>_<situacion>_<formato>`, ver `references/nombres.md`) en segundo plano (imprime la URL y la carpeta de revisión
  `entregas/review/<base>_vNN/`), y `frameback watch entregas/<base>_vNN.mp4 --json --actor human,system` con la
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
  Comentario editado (`revision` > `seenRevision`) → re-planificar (y cancelar el subagente si quedó obsoleto);
  comentario borrado → deshacer lo preparado. Las decisiones de juicio editorial siguen la regla de **Modelo por fase**.
- **Al pulsar "Procesar" (`review.submitted`) — el botón del creador gatilla el entregable:** solo se integra lo ya
  preparado; nada se empieza de cero aquí. Esperar a los subagentes que sigan corriendo, `frameback review <dir>
  --state processing`; promover `edl.next.json` → `edl.json` (con los assets de `edit/staging/`) y renderizar **una
  sola vez** la versión siguiente según
  **Versionado de entregables** (`-o entregas/<base>_v<NN+1>.mp4`; la anterior se archiva al final); marcar cada comentario
  `--status applied --applied-in <base>_v<NN+1>` (o `declined` con razón); `frameback review <dir> --state delivered
  --next-video entregas/<base>_v<NN+1>.mp4` y abrir la nueva versión (`frameback open …`): los comentarios se traspasan
  solos para que el creador verifique. **Detener el watch anterior e iniciar uno nuevo sobre `_v<NN+1>`**: los
  comentarios que el creador reabra ahí vuelven a `pending` y son la siguiente ronda. **Recién después de abrir la
  nueva** (el traspaso de comentarios y el campo `previous` se resuelven buscando la revisión anterior junto a la
  nueva, en `entregas/review/`), archivar la anterior: `python3 edit/deliver.py entregas/<base>_v<NN+1>.mp4` mueve
  `<base>_vNN.*` (video + sidecars) y `entregas/review/<base>_vNN/` juntos a `entregas/anteriores/`. Así la revisión
  vieja sigue reproduciendo su video desde `anteriores/`. `deliver.py` se niega si la nueva aún no tiene revisión.
- **Retro (fase 9):** los comentarios de Frameback son la mejor fuente de aprendizajes: `frameback export <dir>`
  genera un resumen en Markdown para proponer reglas en `<perfil>/aprendizajes.md`.
- **Estados de la revisión:** `delivered` y `closed` se aplican solo a la revisión de la versión **reemplazada**
  (`_vNN`), nunca a la recién abierta (`_v<NN+1>`), que debe quedar en `reviewing`; si no, Frameback bloquea los
  comentarios nuevos y el clic en planos solo mueve el cabezal. Nada de `--force` en estados sin pedido explícito. Si
  se bloqueó por error, el creador puede pulsar **Reopen review** en el panel de comentarios.

