# Modelo relacional

Paso a tablas del modelo entidad-relación ([modelo-er/](modelo-er/README.md)) con los cambios del 6 y 7 de noviembre. Notación: **clave primaria** en negrita, `→ tabla` clave ajena, *UK* valor único.

Cada tabla indica la app de Django donde vive y su dueño según el reparto de la iteración 1. Django pone a cada tabla el prefijo de su app (por ejemplo, `tareas_asignacion`).

## Objetivo 1 · Usuarios y acceso — app `usuarios` (Manu)

- **usuario** (**id**, usuario_acceso *UK*, nombre, apellidos, correo, hash_contrasena, rol, activo, fecha_creacion)
- **clase** (**id**, nombre, curso_escolar, imagen, descripcion_imagen)
  - *UK* (nombre, curso_escolar)
- **estudiante** (**usuario_id** → usuario, codigo_estudiante *UK*, avatar, clase_id → clase, tutor_id → usuario, fecha_alta_tutor, familiar_id → usuario, fecha_alta_familiar)
- **atencion** (**id**, profesional_id → usuario, estudiante_id → estudiante, fecha_alta)
  - *UK* (profesional_id, estudiante_id)
- **imagen_acceso** (**id**, orden *UK*, imagen, descripcion_imagen, activa)

Cómo se ha pasado la generalización USUARIO → ADULTO / ESTUDIANTE → ADMINISTRADOR / TUTOR / PROFESIONAL / FAMILIAR:

- Los atributos de ADULTO (usuario de acceso, correo, contraseña) van en **usuario**, porque Django ya los trae en su modelo de usuario. El estudiante los tiene vacíos y su contraseña no se puede usar.
- Los cuatro tipos de adulto no tienen tabla propia: son valores de `usuario.rol`. La profesora indicó que tutor y profesional solo se diferencian en un permiso.
- ESTUDIANTE sí tiene tabla propia porque tiene atributos y relaciones exclusivas. Su clave es la del usuario (1:1).
- *tutoriza* (1:N) y *es familiar de* (1:N) son claves ajenas en **estudiante**, con su `fecha_alta`. Al ser una sola columna, un estudiante tiene como mucho un familiar (RI1.2.1).
- *atiende* (N:M) es la tabla **atencion**.
- *pertenece* pasa a ser N:1: `estudiante.clase_id`.

Acceso del estudiante (decisión del 7 de noviembre): el estudiante pulsa su avatar y después, según `perfil.metodo_acceso`, escribe una contraseña de texto o elige 3 imágenes de la rejilla común **imagen_acceso**, sin importar el orden. En los dos casos se guarda solo el hash en `usuario.hash_contrasena`; no hay tabla que relacione estudiantes con imágenes. Los adultos entran con usuario y contraseña.

## Objetivo 4 · Perfil — app `perfil` (Jorge)

- **perfil** (**estudiante_id** → estudiante, tema, paleta, tipo_letra, tamano_letra, tamano_botones, posicion_botones, contenido_botones, max_tarjetas, tipo_temporizador, temporizador_visible, puede_ocultar_temporizador, metodo_acceso, usa_lector_pantalla)

PERFIL es entidad débil de ESTUDIANTE (1:1), así que su clave es la del estudiante.

## Horario escolar — app `horario` (Javi)

- **franja** (**id**, orden *UK*, hora_inicio, hora_fin)
- **asignatura** (**id**, nombre *UK*, tipo, imagen, descripcion_imagen)
- **horario_clase** (**id**, clase_id → clase, dia_semana, franja_id → franja, asignatura_id → asignatura)
  - *UK* (clase_id, dia_semana, franja_id)

Cómo funciona:

- **franja** es la rejilla común a todo el centro (franja 1 de 9:00 a 10:00, franja 2 de 10:00 a 11:00…), igual de lunes a viernes.
- **asignatura** es el catálogo de asignaturas y talleres (Matemáticas, Taller de cocina…).
- **horario_clase** es la relación ternaria *se imparte*: qué asignatura o taller tiene cada clase, cada día, en cada franja.
- La clave única (clase, día, franja) **impide los solapes por construcción**: una clase no puede tener dos cosas en la misma franja del mismo día. Es la prueba de aceptación de HU-03-11.
- El horario escolar va de la primera franja a la última. Fuera de ese intervalo es tiempo libre, donde el familiar puede crear tareas para casa (RF3.3.4).

## Objetivo 3 · Tareas — app `tareas` (Úrsula)

- **tarea** (**id**, nombre, descripcion, imagen, descripcion_imagen, ambito, creador_id → usuario)
- **paso** (**id**, tarea_id → tarea, orden, imagen, descripcion_imagen, descripcion)
  - *UK* (tarea_id, orden)
- **asignacion** (**id**, tarea_id → tarea, estudiante_id → estudiante, asignado_por_id → usuario, fecha_asignacion, hora_inicio, hora_fin, dias_semana, vigencia_desde, vigencia_hasta)

Notas:

- PASO es entidad débil de TAREA, con clave parcial `orden`. En el E/R su clave es (tarea, orden); en la tabla se añade un `id` porque Django trabaja mejor con claves de una sola columna, y (tarea_id, orden) queda como *UK*. Es equivalente.
- Los atributos de la antigua PROGRAMACIÓN están ahora en **asignacion**. `dias_semana` es multivaluado y se guarda como lista de enteros (1 = lunes … 7 = domingo), que PostgreSQL admite de forma nativa.
- Los solapamientos entre asignaciones de un mismo estudiante dependen de varias filas (horas, días y vigencia), así que se comprueban en el código (HU-03-03), no con una restricción.

## Objetivo 2 · Ejecución — app `agenda` (Tomás)

- **ejecucion** (**id**, asignacion_id → asignacion, fecha, inicio_real, fin_real, estado)
  - *UK* (asignacion_id, fecha)
- **ejecucion_paso** (**id**, ejecucion_id → ejecucion, paso_id → paso, estado)
  - *UK* (ejecucion_id, paso_id)

Notas:

- Una ejecución es la realización de una asignación en un día concreto. Se crea la primera vez que hace falta (al mostrar la agenda o al empezar la tarea), no por adelantado.
- **ejecucion_paso** es la relación N:M *avanza*, con su atributo `estado_paso`.

## Borrado en cascada (RNF1.1.5)

Al eliminar un estudiante se borran su perfil, sus asignaciones, sus ejecuciones, el avance de sus pasos y sus atenciones. Al eliminar una tarea se borran sus pasos y sus asignaciones. **No** se puede eliminar un usuario que ha creado tareas o asignaciones mientras existan: primero se reasignan. Así no se pierde trabajo de otros sin querer.
