# Diccionario de datos

Descripción de cada campo de las tablas del [modelo relacional](relacional.md). Tipos de PostgreSQL 16. «Nulo: sí» quiere decir que el campo es opcional.

No se guardan fotografías, documentos de identidad ni datos médicos (RNF1.1.3). Las imágenes son archivos subidos al servidor: en la tabla se guarda su ruta.

## Valores permitidos

| Lista | Valores | Por defecto |
| --- | --- | --- |
| rol | `administrador`, `tutor`, `profesional`, `familiar`, `estudiante` | — |
| ambito | `escolar`, `ocio`, `casa` | `escolar` |
| tipo de asignatura | `asignatura`, `taller` | `asignatura` |
| estado de ejecución (RF2.3.1) | `pendiente`, `en_curso`, `tiempo_agotado`, `hecha`, `vencida`, `cancelada`, `no_realizable` | `pendiente` |
| estado de paso | `pendiente`, `hecho` | `pendiente` |
| tema | `claro`, `oscuro` | `claro` |
| paleta | `suave`, `estandar`, `alto_contraste` | `estandar` |
| tipo de letra | `open_sans`, `atkinson`, `lexend` (provisional: lo decide HU-04-01) | `open_sans` |
| tamaño de letra (px) | 16, 20, 24, 32 | 20 |
| tamaño de botones (px) | 48, 64, 80 | 48 |
| posición de botones | `abajo`, `arriba`, `izquierda`, `derecha` | `abajo` |
| contenido de botones | `imagen`, `texto`, `ambos` | `ambos` |
| tipo de temporizador | `lineal`, `radial`, `numerico` | `lineal` |
| días de la semana | 1 = lunes … 7 = domingo | — |

---

## usuario

App `usuarios` · Requisitos: RI1.1.1, RI1.3.1 · Es el modelo de usuario de Django ampliado.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK, autoincremental | Identificador | RI1.1.1 |
| usuario_acceso | varchar(150) | no | UK | Nombre con el que entra un adulto. En los estudiantes se genera solo a partir del código y nunca se usa | RI1.3.1 |
| nombre | varchar(150) | no | no vacío | Nombre | RI1.1.1 |
| apellidos | varchar(150) | sí | | Apellidos | RI1.1.1 |
| correo | varchar(254) | sí | | Correo del adulto (opcional) | E/R |
| hash_contrasena | varchar(128) | no | Argon2 | Hash de la contraseña. En los estudiantes es un valor inutilizable | RNF1.1.4 |
| rol | varchar(20) | no | lista «rol» | Rol del usuario | RI1.1.1 |
| activo | boolean | no | por defecto verdadero | Cuenta activa o desactivada | E/R |
| fecha_creacion | timestamptz | no | automática | Fecha de alta de la cuenta | RI1.1.1 |

En Django, `usuario_acceso` es `username`, `nombre` es `first_name`, `apellidos` es `last_name`, `correo` es `email`, `hash_contrasena` es `password`, `activo` es `is_active` y `fecha_creacion` es `date_joined`. Django añade sus propios campos internos (`last_login`, `is_staff`, `is_superuser`, grupos y permisos), que no forman parte del modelo de datos del proyecto. El bloqueo tras 5 intentos fallidos (RI1.3.1, RNF1.2.3) lo guarda django-axes en sus propias tablas.

## clase

App `usuarios` · Requisito: RI1.1.2

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador | RI1.1.2 |
| nombre | varchar(50) | no | | Nombre del grupo: A, B, PTVAL 1… | RI1.1.2 |
| curso_escolar | varchar(9) | no | formato `2026-2027` | Curso al que pertenece la clase | E/R |
| imagen | varchar(255) | sí | | Ruta de la imagen de la clase | E/R |
| descripcion_imagen | varchar(150) | sí | | Texto alternativo de la imagen | RNF4.1.5 |

*UK* (nombre, curso_escolar).

## estudiante

App `usuarios` · Requisitos: RI1.1.1, RI1.2.1

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| usuario_id | bigint | no | PK, → usuario (rol `estudiante`), cascada | El usuario de este estudiante | E/R |
| codigo_estudiante | varchar(20) | no | UK | Código interno del centro | E/R |
| avatar | varchar(255) | no | | Ruta de la imagen del avatar. Nunca una foto | RF1.2.1 |
| clase_id | bigint | no | → clase, protegida | Clase actual | RI1.1.2 |
| tutor_id | bigint | sí | → usuario (rol `tutor`), protegida | Tutor vinculado | RI1.2.1 |
| fecha_alta_tutor | date | sí | obligatoria si hay tutor | Fecha del vínculo con el tutor | RI1.2.1 |
| familiar_id | bigint | sí | → usuario (rol `familiar`), protegida | Único familiar vinculado | RI1.2.1 |
| fecha_alta_familiar | date | sí | obligatoria si hay familiar | Fecha del vínculo con el familiar | RI1.2.1 |

«Protegida» significa que no se puede borrar la clase, el tutor o el familiar mientras tengan estudiantes vinculados. Que el usuario apuntado tenga el rol correcto se comprueba en el código.

## atencion

App `usuarios` · Requisito: RI1.2.2 · La rellena HU-01-08.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador | — |
| profesional_id | bigint | no | → usuario (rol `profesional`), cascada | Profesional | RI1.2.2 |
| estudiante_id | bigint | no | → estudiante, cascada | Estudiante que atiende | RI1.2.2 |
| fecha_alta | date | no | automática | Fecha en que lo eligió | RI1.2.2 |

*UK* (profesional_id, estudiante_id).

## perfil

App `perfil` · Requisito: RI4.1.1 · Se crea con los valores por defecto al crear el estudiante.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| estudiante_id | bigint | no | PK, → estudiante, cascada | Estudiante | RI4.1.1 |
| tema | varchar(10) | no | lista «tema» | Claro u oscuro | RF4.1.1 |
| paleta | varchar(20) | no | lista «paleta» | Paleta de colores | RF4.1.1 |
| tipo_letra | varchar(20) | no | lista «tipo de letra» | Tipo de letra | RF4.1.2 |
| tamano_letra | smallint | no | lista «tamaño de letra» | Tamaño en px CSS | RF4.1.2 |
| tamano_botones | smallint | no | lista «tamaño de botones» | Lado mínimo de los botones en px CSS | RF4.1.3 |
| posicion_botones | varchar(10) | no | lista «posición de botones» | Dónde van botones y menús (HU-04-06, iteración 3) | RF4.1.4 |
| contenido_botones | varchar(10) | no | lista «contenido de botones» | Imagen, texto o ambos (HU-04-02, iteración 2) | RF4.2.4 |
| max_tarjetas | smallint | no | entre 1 y 6, por defecto 6 | Máximo de tarjetas en la vista de día | RF4.2.2 |
| tipo_temporizador | varchar(10) | no | lista «tipo de temporizador» | Lineal, radial o numérico | RF4.3.3 |
| temporizador_visible | boolean | no | por defecto verdadero | Si el temporizador se ve al empezar | RF4.3.1 |
| puede_ocultar_temporizador | boolean | no | por defecto falso | Si el estudiante puede ocultarlo | RF4.3.1 |

Los campos de iteraciones posteriores (posición y contenido de botones) se crean ya con su valor por defecto, para no tener que migrar la tabla después.

## franja

App `horario` · Requisito: RI3.4 · Rejilla horaria común a todo el centro, igual de lunes a viernes.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador | — |
| orden | smallint | no | UK, mayor que 0 | Posición en el día (1.ª, 2.ª…) | — |
| hora_inicio | time | no | | Hora de inicio | RI3.4 |
| hora_fin | time | no | posterior a hora_inicio | Hora de fin | RI3.4 |

Que dos franjas no se solapen se comprueba en el código al guardarlas.

## asignatura

App `horario` · Requisito: RI3.4 · Catálogo de asignaturas y talleres.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador | — |
| nombre | varchar(80) | no | UK | Nombre: Matemáticas, Taller de cocina… | RI3.4 |
| tipo | varchar(15) | no | lista «tipo de asignatura» | Asignatura o taller | Profesora |
| imagen | varchar(255) | no | | Ruta de la imagen | RI3.4 |
| descripcion_imagen | varchar(150) | no | | Texto alternativo de la imagen | RNF4.1.5 |

## horario_clase

App `horario` · Requisitos: RI3.4, HU-03-11 · Relación ternaria *se imparte*: una casilla del horario de una clase.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador | — |
| clase_id | bigint | no | → clase, cascada | Clase | RI3.4 |
| dia_semana | smallint | no | de 1 a 5 | Día lectivo (1 = lunes … 5 = viernes) | RI3.4 |
| franja_id | bigint | no | → franja, protegida | Franja horaria | RI3.4 |
| asignatura_id | bigint | no | → asignatura, protegida | Asignatura o taller en esa franja | RI3.4 |

*UK* (clase_id, dia_semana, franja_id): impide dos asignaturas a la vez en la misma clase.

## tarea

App `tareas` · Requisito: RI3.1.1 · Catálogo de tareas del centro.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador | RI3.1.1 |
| nombre | varchar(80) | no | no vacío | Nombre de la tarea | RF3.1.1 |
| descripcion | text | sí | | Descripción en texto | RF3.1.2 |
| imagen | varchar(255) | no | | Ruta de la imagen (ARASAAC o subida) | RF3.1.1, profesora |
| descripcion_imagen | varchar(150) | no | | Descripción de la imagen; es su texto alternativo | Profesora, RNF4.1.5 |
| ambito | varchar(10) | no | lista «ámbito» | Escolar, ocio o casa | RF3.3.1 |
| creador_id | bigint | no | → usuario, protegida | Quién la creó | RI3.1.1 |

Sin fecha de creación ni estado (profesora).

## paso

App `tareas` · Requisito: RI3.1.3 · Entidad débil de tarea.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador técnico | — |
| tarea_id | bigint | no | → tarea, cascada | Tarea a la que pertenece | RI3.1.3 |
| orden | smallint | no | mayor que 0 | Posición del paso en la tarea | RI3.1.3 |
| imagen | varchar(255) | no | | Ruta de la imagen | RF3.1.3 |
| descripcion_imagen | varchar(150) | no | | Texto alternativo de la imagen | RNF4.1.5 |
| descripcion | text | sí | | Explicación del paso (antes «texto opcional») | RF3.1.3, profesora |

*UK* (tarea_id, orden).

## asignacion

App `tareas` · Requisitos: RI3.2.1, RI3.2.2 · Incluye los atributos de la antigua PROGRAMACIÓN.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador | RI3.2.1 |
| tarea_id | bigint | no | → tarea, cascada | Tarea asignada | RI3.2.2 |
| estudiante_id | bigint | no | → estudiante, cascada | Estudiante que la recibe | RI3.2.2 |
| asignado_por_id | bigint | no | → usuario (tutor, profesional o familiar), protegida | Quién la asignó | RI3.2.2 |
| fecha_asignacion | timestamptz | no | automática | Cuándo se asignó | RI3.2.2 |
| hora_inicio | time | no | | Hora de inicio prevista | RI3.2.1 |
| hora_fin | time | no | posterior a hora_inicio | Hora de fin prevista | RI3.2.1, RF3.2.2 |
| dias_semana | smallint[] | no | al menos un día; valores de 1 a 7 | Días en que se repite | RI3.2.1, RF3.2.2 |
| vigencia_desde | date | no | | Primer día en que aplica | RI3.2.1 |
| vigencia_hasta | date | sí | igual o posterior a vigencia_desde | Último día; vacío = sin fecha de fin | RI3.2.1 |

Que no se solape con otra asignación del mismo estudiante se comprueba en el código (RF3.2.3). Que el administrador no asigne se comprueba en el código (anotación del E/R).

## ejecucion

App `agenda` · Requisito: RI2.1.1 · La realización de una asignación en un día concreto.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador | RI2.1.1 |
| asignacion_id | bigint | no | → asignacion, cascada | Asignación que se ejecuta. Por ella se llega a la tarea y al estudiante | RI2.1.1 |
| fecha | date | no | | Día de la ejecución | RI2.1.1 |
| inicio_real | timestamptz | sí | | Marca de inicio (hora del servidor) | RI2.1.1, RF2.3.3 |
| fin_real | timestamptz | sí | igual o posterior a inicio_real | Marca de fin | RI2.1.1, RF2.3.6 |
| estado | varchar(20) | no | lista «estado de ejecución» | Estado actual | RF2.3.1 |

*UK* (asignacion_id, fecha). En el E/R y en RI2.1.1 aparecen también la tarea y el estudiante; aquí se obtienen a través de la asignación, para no guardar el mismo dato dos veces.

## ejecucion_paso

App `agenda` · Requisito: RI2.1.2 · Relación *avanza*.

| Campo | Tipo | Nulo | Restricciones | Descripción | Origen |
| --- | --- | --- | --- | --- | --- |
| id | bigint | no | PK | Identificador técnico | — |
| ejecucion_id | bigint | no | → ejecucion, cascada | Ejecución | RI2.1.2 |
| paso_id | bigint | no | → paso, cascada | Paso | RI2.1.2 |
| estado | varchar(10) | no | lista «estado de paso» | Pendiente o hecho | RI2.1.2 |

*UK* (ejecucion_id, paso_id).
