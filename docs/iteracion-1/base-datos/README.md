# Diseño de la base de datos

Responsables: Javier y Úrsula (revisión de privacidad: Lara-Marie y Kaya). Diseño lógico cerrado el 7 de noviembre de 2026 a partir del E/R revisado por la profesora.

| Archivo | Contenido | Tarea |
| --- | --- | --- |
| [modelo-er/](modelo-er/README.md) | Cambios que hay que aplicar al diagrama de draw.io y diagrama lógico | T14 |
| [relacional.md](relacional.md) | Tablas, claves y cómo se ha pasado cada parte del E/R | T16 |
| [diccionario.md](diccionario.md) | Cada campo: tipo, si es opcional, restricciones y requisito de origen | T16 |

## Decisiones principales

1. **Un único usuario con rol.** Tutor, profesional, familiar y administrador no tienen tabla propia: son valores de `rol`. El estudiante sí tiene tabla, porque tiene atributos propios (código, avatar, clase, vínculos).
2. **Horario escolar en tres tablas.** `franja` es la rejilla de horas común a todo el centro, igual todos los días. `asignatura` es el catálogo de asignaturas y talleres. `horario_clase` dice qué tiene cada clase, cada día y en cada franja. Por cómo está construido, una clase nunca puede tener dos cosas a la vez.
3. **Programación dentro de asignación**, como pidió la profesora.
4. **Imagen y descripción de la imagen** en todas las entidades que se muestran con imagen. La descripción sirve además de texto alternativo (RNF4.1.5).
5. **Cada estudiante pertenece a su clase actual** (N:1). El histórico por curso queda fuera de la iteración 1.
6. **Las reglas de una sola fila van en la base de datos** (únicos, horas coherentes, rangos). Las que dependen de varias filas, como los solapamientos entre asignaciones, van en el código de su dueño.

## Correspondencia con el código

Cada tabla vive en la app de su objetivo, que se indica en el diccionario. Las tablas de Django llevan el prefijo de su app (`tareas_asignacion`). Sin campos de fotografías, documentos de identidad ni datos médicos (RNF1.1.3).
