# Diseño de la base de datos

Responsables: Javier y Úrsula (revisión de privacidad: Lara-Marie y Kaya).

| Archivo | Contenido | Tarea |
| --- | --- | --- |
| `modelo-er/` | Diagrama entidad-relación (exportado a PNG o SVG, más el archivo fuente de la herramienta) | T14 |
| [relacional.md](relacional.md) | Tablas normalizadas con claves primarias y ajenas | T16 |
| [diccionario.md](diccionario.md) | Cada campo: tipo, obligatoriedad, restricciones y requisito de origen | T16 |

## Correspondencia con el código

Cada tabla irá en la app de su objetivo (`apps/<app>/models.py`). Las entidades previstas están anotadas en el `models.py` de cada app. Convenciones para pasar del diccionario a Django:

- Nombres de tabla y campo en `snake_case`; Django pone el prefijo de la app (`agenda_ejecucion`).
- Claves primarias: `BigAutoField` automático (`id`).
- Restricciones del diccionario como `constraints` en `Meta` (p. ej. un solo familiar por estudiante, RI1.2.1, con `UniqueConstraint` condicional).
- Sin campos de fotografías, documentos de identidad ni datos médicos (RNF1.1.3).
