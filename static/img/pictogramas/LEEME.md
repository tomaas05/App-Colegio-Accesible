# Pictogramas de la interfaz

Pictogramas: Sergio Palao. Origen: ARASAAC (arasaac.org). Licencia: CC BY-NC-SA. Propiedad: Gobierno de Aragón.

Aquí van los pictogramas que usa la propia interfaz (portada, rejilla de entrada del
estudiante, avatares). Se descargan **una sola vez** y se suben al repositorio, para que
la aplicación no dependa de Internet al ejecutarse (decisión 0004):

1. Añade a `listado.csv` una línea por pictograma: `id;nombre` (el número es el de la
   dirección del pictograma en arasaac.org; el nombre, en minúsculas y sin espacios).
2. `python manage.py descargar_pictogramas`
3. Sube al repositorio los `.png` nuevos junto con `listado.csv`.

El listado está vacío porque los números hay que comprobarlos uno a uno en arasaac.org
(ver «Preguntas para el equipo» en docs/iteracion-1/auditoria-ui.md).
