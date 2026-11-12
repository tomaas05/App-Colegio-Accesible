# Pictogramas de la interfaz

Pictogramas: Sergio Palao. Origen: ARASAAC (arasaac.org). Licencia: CC BY-NC-SA. Propiedad: Gobierno de Aragón.

Aquí van los pictogramas que usa la propia interfaz (portada, clases, avatares, rejilla de
entrada, tareas de prueba). Se descargan **una sola vez** y se suben al repositorio, para que
la aplicación no dependa de Internet al ejecutarse (decisión 0004).

`listado.csv` tiene una línea por pictograma: `nombre;palabra;id`.

- `nombre`: el nombre del archivo (`mochila` → `mochila.png`).
- `palabra`: lo que se busca en ARASAAC si no hay `id` (se toma el primer resultado, como hace el boceto v3).
- `id`: el número del pictograma. Si lo pones, se descarga ese y no se busca.

```bash
python manage.py descargar_pictogramas          # descarga los que falten y apunta su id
python manage.py cargar_datos_prueba            # los datos de prueba ya salen con pictogramas
```

Si un pictograma no te gusta: busca otro en arasaac.org, pon su número en `id`, borra el
`.png` y vuelve a lanzar el comando.
