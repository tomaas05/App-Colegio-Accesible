# Avatares del estudiante

Avatares: «Fun Emoji» de Davis Uche, generados con [DiceBear](https://www.dicebear.com/styles/fun-emoji/). Licencia: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Se han elegido solo caras alegres y se han pasado a PNG de 256 × 256.

Retrospectiva del 19/11: los avatares eran pictogramas de animales de ARASAAC, del mismo estilo
que las 12 imágenes de la contraseña (y alguno repetido: gato, perro, pez). Ahora son una
categoría aparte, sencilla y simpática, para que el estudiante no confunda «quién soy» con
«mi contraseña».

`listado.csv` tiene una línea por avatar: `nombre;palabra`.

- `nombre`: el archivo (`miel` → `miel.png`) y la clave que se guarda.
- `palabra`: el nombre que ve el administrador al elegirlo y el que lee el lector de pantalla.

El código está en `apps/usuarios/avatares.py`. Para añadir uno: genera el PNG con el mismo
estilo (ojos y boca alegres, un color de fondo que no tenga otro), déjalo aquí y añade su línea
al listado. Al crear una cuenta sin elegir avatar, se usa uno de la galería según su código
(A01, el primero; A02, el segundo…).
