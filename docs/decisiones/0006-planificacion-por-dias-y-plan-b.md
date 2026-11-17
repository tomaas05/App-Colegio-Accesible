# 0006 · Cambiar o cancelar un solo día, avisos y plan B ordenado

- **Estado:** propuesta (rama `fix/planificadas-y-plan-b`, pendiente de revisión del equipo)
- **Fecha:** 2026-11-17
- **Responsable:** Tomás, sobre HU-03-04, HU-03-05 y HU-03-06 de Úrsula

## Contexto

La primera versión de HU-03-04 (modificar), HU-03-05 (cancelar) y HU-03-06 (plan B) funcionaba,
pero tenía fallos que la iteración 2 no puede arrastrar, porque HU-02-06 (mi semana), HU-07-04
(elegir un plan B) y HU-06-02 (alertas de plan B, Manu) se apoyan en ellas:

1. «Solo este día» quitaba un **día de la semana** de la serie: cambiar el jueves 19 quitaba
   todos los jueves. RF3.5.2 y RI3.2.3 hablan de una fecha concreta.
2. Una tarea cancelada **desaparecía** de la agenda; HU-03-05 PA1 pide que salga «Cancelada».
3. Cualquier tutor, profesional o familiar podía cambiar o cancelar tareas de **cualquier**
   estudiante (se comprobó con tutor2, profesional y familiar2: todos entraban).
4. El plan B era un ManyToMany **sin orden**; RF3.4.3 pide prioridad.
5. El aviso al estudiante salía como texto con estilos en línea, se daba por leído solo con
   abrir la agenda y no tenía pictograma.
6. Otros: filtros que se enviaban solos al cambiar (WCAG 3.2.2), un `<main>` dentro de otro en
   la confirmación, el campo «aula» (se quita: va con la clase, no con la tarea).

## Decisión

- **Excepciones por fecha** (`excepcion_asignacion`): «Solo este día» guarda otras horas o
  «cancelada» para esa fecha. La serie no cambia. Si se vuelven a poner las horas de siempre, la
  excepción se borra.
- **Cancelar la serie** marca `cancelada` y `cancelada_el` (hoy, o mañana si hoy ya la había
  empezado: lo empezado no se cancela, PA2). El estudiante la ve tachada, «✕ Cancelada», durante
  7 días (`DIAS_VISIBLE_CANCELADA`); no se abre ni se puede empezar.
- **Una sola fuente de verdad** para «qué tareas tiene un estudiante un día y a qué hora»:
  `apps/tareas/planificacion.py` (`ocurrencias_del_dia`). La usan la agenda del estudiante, la
  consulta del profesional (B27), la lista de planificadas y la comprobación de solapes, que así
  tiene en cuenta los cambios de un día y no cuenta lo cancelado. HU-02-06 (semana) la usará.
- **Permisos** (`planificacion.puede_cambiar`): solo estudiantes que la persona ve
  (`estudiantes_de`); el tutor, todo salvo lo que puso el familiar (RF3.3.5); profesional y
  familiar, solo lo que pusieron ellos. Lo demás da 404 (no se dice que existe).
- **Plan B ordenado** (`plan_b`, con `orden`) en su propia pantalla (B42), a la que se llega
  desde el catálogo: añadir del catálogo, crear una nueva (nombre y pictograma), subir, bajar y
  quitar. Todo funciona sin JavaScript. Ya no se elige al crear la tarea.
- **Avisos** (`comun.Notificacion` con `tipo`, `tarea` y `vista_el`): el estudiante ve uno por
  pantalla, antes de su agenda, con el pictograma de la tarea, una frase y «Entendido». Se da
  por visto al pulsar «Entendido» (queda la hora), no al abrir la pantalla. HU-07-04 lo usará
  para avisar al tutor.

## Alternativas descartadas

- **Partir la serie** al cambiar un día (cerrar la vigencia y crear dos asignaciones): multiplica
  las filas, pierde la relación con las ejecuciones ya hechas y complica deshacer el cambio.
- **Borrar la asignación al cancelar:** se pierde el historial y el estudiante no ve que se ha
  cancelado.
- **Avisos que se dan por leídos al mostrarse:** un estudiante puede no haberlo visto (otra
  persona abrió la tableta, se salió enseguida); con «Entendido» queda constancia (HU-07-05).

## Consecuencias

- Cambiar las horas de **toda la serie** cambia también cómo se ven los días pasados en la
  consulta del profesional (la serie es una sola fila). Las ejecuciones guardan su hora real, así
  que no se pierde lo que se hizo.
- Las pantallas que listen tareas de un día deben usar `planificacion.ocurrencias_del_dia`, no
  filtrar `Asignacion` por su cuenta.
- La migración `tareas.0007` copia el plan B antiguo (en el orden en que se añadió) y fecha las
  cancelaciones antiguas con el día de la migración. Se puede deshacer.

## Ampliación (HU-07-04 y HU-02-07, rama `feat/confirmar-y-plan-b-estudiante`)

- **Qué tareas tienen «No puedo hacerla»:** las del ámbito escolar, pendientes o en marcha
  (RF2.15.1 dice «del horario escolar»). Las de ocio y casa no (en B07 las de casa no lo
  tienen; la reprografía tampoco tiene plan B, según las notas del boceto).
- **Lo puede marcar el estudiante** («No puedo hacerla», después de confirmar) **o un adulto**
  que pueda cambiar esa tarea (`planificacion.puede_cambiar`), desde «Tareas planificadas» con
  el día de hoy elegido, diciendo el motivo (RF2.15.1). Solo hoy: para otro día se cancela ese
  día (HU-03-05).
- **Elegir del plan B** (B11) cambia la tarea de ese día por la alternativa
  (`Ejecucion.plan_b`): misma hora, sus pasos, se empieza y se termina como cualquier otra.
  Se elige una vez; si tampoco se puede, se queda como «No se ha podido».
- **El tutor se entera** con un aviso cuando el estudiante elige (dice qué ha elegido), cuando no
  hay plan B, cuando tampoco puede la alternativa y cuando lo marca otro adulto. Lo ve en su
  panel, uno cada vez, con «Visto». Es lo mínimo de PA5; las alertas completas (B28) son de
  HU-06-02 (Manu), que puede leer `Notificacion` con `tipo = plan_b` y `Ejecucion.plan_b`.
- **Confirmar** (HU-02-07): «Terminar» y «No puedo hacerla» usan la misma ventana
  (`agenda/_confirmar.html`): pictograma de la tarea, una frase y «Sí» / «No», con el foco en
  «No». Sin JavaScript, la misma pregunta en una página (`agenda/confirmar.html`).
- **Cómo se ha sentido** con la alternativa (RF2.15.2 → RF6.1.1) queda para HU-06-01
  (iteración 3).
