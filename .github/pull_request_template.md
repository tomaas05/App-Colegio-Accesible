## Qué cambia

<!-- Una o dos frases. -->

**Historia / tarea de Jira:** AGENDA-

**Requisitos que cubre:** RF…, RNF…

## Cómo probarlo

1.

## Comprobaciones

- [ ] `pytest`, `ruff check .` y `pytest -m e2e` pasan en local (resultado pegado abajo mientras la CI no funcione)
- [ ] He añadido la pantalla nueva a `tests/e2e/test_accesibilidad.py` (si hay pantalla nueva)
- [ ] Elementos táctiles ≥ 48 × 48 px y foco visible
- [ ] Sin peticiones a servicios externos desde el navegador (RNF1.1.2)
- [ ] Migraciones incluidas (si cambian modelos)
