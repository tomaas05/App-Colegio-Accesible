# 0004 · Pictogramas de ARASAAC

- **Estado:** propuesta (rama `mejora-ui-bocetos`). **Pendiente: probar contra ARASAAC real** (ver «Sin verificar»).
- **Fecha:** 2026-11-11
- **Responsable:** Úrsula (tareas)

## Contexto

La versión provisional de «Crear tarea» hacía que el navegador llamara a `api.arasaac.org` y cargara
imágenes de `static.arasaac.org`. Eso incumple RNF1.1.2 (ninguna petición del navegador a terceros).
Además el servidor descargaba con `requests.get` sin tiempo máximo, sin validar el identificador y
sin límite de tamaño, y el HTML del paso se escribía en Python con estilos y `onclick`.

## Decisión

- **El navegador solo habla con nuestro servidor.** `apps/comun/pictogramas.py` es lo único que sale a
  ARASAAC, y solo envía la palabra buscada o el número del pictograma: ningún dato de personas.
- **Buscador:** `GET /pictogramas/buscar/?q=…&campo=…` (`pictogramas:buscar`). Solo lectura, con sesión y
  solo adultos (un estudiante recibe 403). Valida `q` (2 a 40 letras, números, espacios o guiones),
  tiempo máximo de 3 s de conexión y 5 s de lectura, caché de Django de un día por palabra, 30 búsquedas
  por minuto y usuario, como mucho 12 resultados. Devuelve un parcial para HTMX.
- **Imágenes siempre locales:** `GET /pictogramas/<id>.png` (`pictogramas:vista_previa`) y el guardado de
  la tarea usan `pictogramas.obtener(id)`: valida que el identificador es un número, descarga una sola vez
  (mismo tiempo máximo, 512 kB como mucho, Pillow comprueba que es un PNG de hasta 1024 px) y guarda
  `media/pictogramas/<id>.png`. Esa copia la comparten todas las tareas y pasos que usan el pictograma
  (`imagen.name = "pictogramas/<id>.png"`). Las vistas previas llevan `Cache-Control` de un año.
- **Si ARASAAC falla:** mensaje en la región `role="status"` y se puede subir un archivo propio. Si falla
  al guardar, la tarea no se guarda a medias y el pictograma sigue elegido para reintentar.
- **Selector accesible:** cada pictograma es un botón de opción con su imagen y su palabra (el nombre
  accesible es la palabra), más la opción «Ninguno». El número de resultados va a una región viva fija;
  el foco se queda en el buscador. El elegido se distingue por borde grueso y «✓», no solo por color.
  Sin `onclick`, sin estilos en línea y sin HTML en Python: `tareas/_buscador_pictograma.html`,
  `tareas/_paso.html` y `comun/_pictogramas_resultados.html`.
- **Pictogramas de la interfaz:** `python manage.py descargar_pictogramas` lee
  `static/img/pictogramas/listado.csv` (`id;nombre`) y los guarda una vez en `static/img/pictogramas/`.
  La aplicación no depende de Internet al ejecutarse.
- **Licencia y atribución:** CC BY-NC-SA. La atribución está en el pie de todas las pantallas, en el
  README y en `static/img/pictogramas/LEEME.md`: «Pictogramas: Sergio Palao. Origen: ARASAAC
  (arasaac.org). Licencia: CC BY-NC-SA. Propiedad: Gobierno de Aragón.»
- **Pruebas sin Internet:** el fixture `arasaac` (`tests/arasaac_falso.py`) sustituye la red. Si una prueba
  intenta salir sin él, falla con un mensaje claro.
- Sin dependencias nuevas: `requests` y `Pillow` ya estaban.

## Sin verificar

Esta decisión se escribió en un entorno sin salida a `arasaac.org`:

- No se ha leído la documentación oficial de la API. Las rutas son las que ya usaban el boceto v3 y la
  app: `https://api.arasaac.org/v1/pictograms/es/search/<texto>` (lista de objetos con `_id` y
  `keywords[].keyword`; 404 si no hay resultados) y
  `https://static.arasaac.org/pictograms/<id>/<id>_300.png`. Se cambian con los ajustes
  `ARASAAC_URL_BUSQUEDA` y `ARASAAC_URL_IMAGEN`.
- No se conocen límites de uso publicados; por eso la caché y el límite por usuario.
- La licencia se ha contrastado en fuentes secundarias (CATEDU, Aula Abierta de ARASAAC), no en las
  condiciones de uso de arasaac.org.
- El listado de pictogramas de la interfaz está vacío: hay que elegir los números mirándolos en arasaac.org.

## Alternativas descartadas

- **Que el navegador cargue de ARASAAC:** incumple RNF1.1.2 y enseña a ARASAAC la IP de cada tableta.
- **Copiar el pictograma a cada tarea:** duplica archivos; la copia compartida basta.
- **Descargar todo ARASAAC:** más de 600 MB.

## Consecuencias

- Con varios procesos del servidor, la caché por defecto de Django es de cada proceso: el límite por
  usuario se multiplica por el número de procesos. Para la demo vale; si no, caché en base de datos.
- `media/pictogramas/` crece con el uso; un pictograma pesa entre 10 y 60 kB.
- Uso **no comercial** y obligación de **compartir igual**: ver las preguntas de `docs/iteracion-1/auditoria-ui.md`.
