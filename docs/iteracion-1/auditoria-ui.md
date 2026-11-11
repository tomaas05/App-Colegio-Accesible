# Auditoría de interfaz · mejora `mejora-ui-bocetos`

- **Fecha:** 2026-11-11 · **Rama:** `mejora-ui-bocetos` (desde `main` en `00a460a`)
- **Herramientas:** pytest, Playwright + axe-core, Lighthouse 12 (móvil y escritorio), skill `a11y-colegio` (axe, recorrido con Tab, tamaños y separación de objetivos).
- **Fuente de verdad visual:** `docs/iteracion-1/bocetos/despega_mockup_v3.html`.
- Las capturas no se suben al repositorio.

## 1. Línea base (antes de tocar nada)

| Qué | Resultado |
| --- | --- |
| `pytest` | 388 pasan, 2 fallan (las 2 de ARASAAC, que salían a Internet) |
| `pytest -m e2e tests/e2e` | 113 pasan |
| `ruff check .` | sin avisos |
| CSS propio / JS propio / HTMX / fuentes | 55,8 kB / 27,4 kB / 52,2 kB / 133,7 kB (sin comprimir) |

Lighthouse móvil (servidor de desarrollo, sin compresión): Rendimiento 93–100, Accesibilidad 100
(98 en «Crear tarea» por el orden de encabezados), Buenas prácticas 96, LCP 1,06–1,69 s,
CLS ≤ 0,036, ninguna petición a terceros **al cargar**. El detalle y el «después» están en el apartado 6.

## 2. Tabla boceto → URL → diferencias

Las pantallas del boceto que no tienen URL son de la iteración 2 y no se implementan.

| Boceto | URL real | Estado tras la mejora | Diferencias que quedan |
| --- | --- | --- | --- |
| B01 Inicio | `/` | Alineada | Los dibujos son emojis; pasarán a pictogramas con `descargar_pictogramas` (apartado 7) |
| B02 ¿Cuál es tu clase? | `/estudiante/` | Alineada | Igual que B01 para las clases sin imagen |
| B03 ¿Quién eres? (avatares) | `/estudiante/clase/<id>/` | Alineada | El boceto pagina la rejilla para que quepa sin desplazarse; la app se desplaza en vertical |
| — (3 imágenes o contraseña) | `/estudiante/<código>/entrar/` | Sin boceto | Rejilla de 12 imágenes con marcadores; pendiente de pictogramas |
| B12 Entrar (adultos) | `/entrar/` | Alineada | — |
| B13 Panel | `/panel/` | Alineada + panel lateral | El boceto pone icono y flecha en cada opción; la app solo texto (propuesta) |
| B20 Usuarios | `/usuarios/` | Parcial | El boceto usa tarjetas con editar y borrar y filtro por estado; la app, tabla sin editar ni borrar (funcionalidad de It2) |
| B21 Crear cuenta | `/usuarios/nueva/` | Alineada | — |
| B22 / B29 Clases | administración de Django | No alineada | Pantalla propia pendiente (It2) |
| B25 Vínculos | `/usuarios/vinculos/` | Alineada | — |
| B26 Elegir mis estudiantes | `/panel/mis-estudiantes/` | Alineada | 35 paradas de foco en el boceto y parecido en la app: ver propuestas |
| B27 Agenda de un estudiante | `/panel/mis-estudiantes/<código>/agenda/` | Parcial | El boceto tiene vista Día/Semana/Mes y huecos libres; la app, solo día (It2). Corregido el estado «Vencida» |
| B37 Horario escolar | `/horario/` | Alineada | — |
| B05 Horario | `/horario/mi-horario/` | Alineada | Lista hacia abajo, como pidió la profesora |
| B06 Tareas de hoy | `/agenda/` | Alineada | El boceto tiene «‹ Menú», «Semana» y «Ocio» (B04, B30 y B31 son de It2). Añadido «Salir» |
| B07 Tarea · B08 ¿Has terminado? | `/agenda/tarea/<id>/` | Alineada | «No puedo hacerla» y plan B son de It2 |
| B40 Crear tarea · B41 Pasos | `/tareas/crear/` | Rehecha | El boceto es un asistente de 5 pasos con plan B; la app, un formulario con vista previa. Manda la función |
| B43 Asignar a estudiantes | `/tareas/asignar/` | Rehecha | El boceto asigna al terminar de crear; la app, desde el catálogo |
| — (catálogo) | `/tareas/catalogo/` | Rehecha | En el boceto es el paso «1. Buscar» de B40 |
| B52 Perfil visual · B54 Temporizador | `/perfil/` · `/perfil/<código>/` | Alineada | Solo se ha unificado la cabecera |
| B04, B09–B11, B14, B15, B23, B28, B30–B36, B42, B44, B46, B50, B51, B53, B55, B56, B60–B68 | — | Iteración 2 | No se implementan |

## 3. Fallos encontrados

| # | Fallo | Verificado | Estado | Prueba |
| --- | --- | --- | --- | --- |
| 7 | `apps/tareas`: solo `@login_required`; un estudiante creaba y asignaba; salían todos los estudiantes; `print()`; id de ARASAAC sin validar; `requests.get` sin tiempo máximo | Sí | Corregido | `tests/test_pictogramas.py` |
| 8 | `perfil_estudiante` llamaba a `logout()` | Sí | Corregido (middleware) | `tests/test_mejora_fallos.py` |
| 9 | Agenda de «Mis estudiantes»: «Pendiente» en días pasados; 500 con `?dia=9999-12-31` | Sí | Corregido | ídem |
| 10 | Estudiante sin «Salir» | Sí | Corregido (cabecera común) | `tests/test_estructura_comun.py` |
| 11 | 48 `style=` y 11 `onclick=` (todos en `apps/tareas`) | Sí | Corregido: 0 y 0 | `test_el_formulario_no_lleva_estilos_ni_eventos_en_linea` |
| 12 | README con la fila de `/perfil/` duplicada | Sí | Corregido | `test_el_readme_no_repite_la_fila_del_perfil` |
| 13 | Marcadores de imagen con tildes como cuadros | Sí (la fuente de Pillow dibuja el mismo cuadro para Á, É y Ñ) | Corregido (Nunito) | `test_las_letras_con_tilde_se_dibujan…` |
| 14a | «Crear tarea»: el navegador llamaba a `api.arasaac.org` y `static.arasaac.org` (RNF1.1.2) | Sí | Corregido | e2e `test_buscador_de_pictogramas…` |
| 14b | «Crear tarea»: al volver con errores se perdían los pasos escritos | Sí | Corregido | `test_los_pasos_no_se_pierden…` |
| 14c | «Crear tarea»: la vista previa metía el nombre con `innerHTML` (HTML inyectable) y validaba con `alert()` | Sí | Corregido (`textContent`, errores del servidor con resumen) | — |
| 14d | «Crear tarea» cargaba HTMX dos veces | Sí | Corregido | — |
| 14e | «Asignar»: dos `<main>` anidados y errores en un `<dialog>` | Sí | Corregido | e2e de tareas |
| 14f | «Catálogo»: colores fijos fuera de la paleta (`#007bff` con blanco, 3,98:1), objetivos de 44 px, una consulta por tarea | Sí | Corregido | `test_el_catalogo_no_hace_una_consulta_por_tarea` |
| 14g | 403 y 404 sin página propia | Sí | Corregido | `tests/test_mejora_fallos.py` |
| 14h | Letra menor de 16 px en 5 reglas (14,4 y 15,2 px) y foco de 3 px | Sí | Corregido (16 px y 4 px) | — |
| 14i | `test_la_agenda_no_ofrece_modificar_ni_borrar` exigía que no hubiera ningún `<form>` | — | Ajustada: ahora el único es «Salir» | — |

## 4. `a11y-colegio` sobre el boceto v3 (18 pantallas de la iteración 1)

Medido a 1024×768 y 390×844, sin conexión a ARASAAC ni a Google Fonts (el boceto las pide; se ven
los emojis y Arial de reserva).

- **axe:** ninguna infracción WCAG 2.2 AA en las 18 pantallas.
- **Trampa de foco (crítico, 2):** `input[type=time]` en B43 y B37. Probable falso positivo: Tab recorre
  horas y minutos dentro del campo. **Hay que comprobarlo a mano con pulsador.**
- **Demasiadas paradas de foco:** B26 (35), B20 (31), B27 (17–18), B41 (17), B43 (14). El umbral de 12 es
  un criterio del proyecto, no de WCAG. En pantallas de adultos es aceptable; no trasladar ese patrón al estudiante.
- **Letra pequeña:** 11 px en una marca de cambios (es de la herramienta del boceto) y 15 px en textos secundarios de B07 y B27. En la app el mínimo es ya 16 px.
- **Orden de foco frente a orden visual (15 avisos):** casi todos son grupos de botones que saltan de línea. Revisado a ojo: el orden es el de lectura.
- **Sin «Saltar al contenido»** en el boceto (la app sí lo tiene).
- **El boceto llama desde el navegador a ARASAAC y a Google Fonts.** Vale para un boceto; la app no puede (RNF1.1.2) y no lo hace.
- **Pantallas del estudiante:** 2–9 paradas de foco, objetivos de 48 px o más. Bien.

No medido: lector de pantalla real, pulsador real, tableta del colegio, personas.

## 5. `a11y-colegio` sobre la app (después de la mejora)

| Pantalla | Crítico | Alto | Medio | Paradas (tableta / móvil) |
| --- | --- | --- | --- | --- |
| Portada | 0 | 0 | 0 | 4 / 4 |
| Agenda del estudiante | 0 | 0 | 0 | 9 / 9 |
| Tarea | 0 | 0 | 0 | 5 / 5 |
| Panel del tutor | 0 | 1* | 0 | 10 / 6 |
| Crear tarea | 0 | 1* | 1 (18 paradas) | 18 / 14 |
| Usuarios | 0 | 1* | 3 | 25 / 25 |

\* Falso positivo explicado: el salto «sube» es pasar de «Salir» (final del panel lateral, columna
izquierda) al principio del contenido (columna derecha). El DOM va en orden: cabecera, panel, contenido.

Pendiente en «Usuarios» (Manu): enlaces de la tabla que se tocan con el borde de la caja con
desplazamiento, y 25 paradas (15 filas). Se propone, no se aplica.

## 6. Cifras de antes y después

| Qué | Antes | Después |
| --- | --- | --- |
| `pytest` | 388 pasan, 2 fallan sin Internet | **504 pasan, 0 fallan** (sin Internet) |
| `pytest -m e2e` | 113 | **141** |
| `ruff check .` | limpio | limpio |
| `style=` (48 en plantillas y vistas, 7 en JS) / `onclick=` / `print()` / `alert()` | 55 / 11 / 6 / 2 | 0 / 0 / 0 / 0 |
| CSS propio | 55,8 kB | 58,1 kB (+ estructura común, − `tarea.css` antiguo) |
| JS propio | 27,4 kB | 22,7 kB |
| Imágenes en `static/img` | 0 | 23,4 kB (logotipo WebP 6 kB, icono y favicon) |

Lighthouse móvil (Rendimiento / Accesibilidad / Buenas prácticas · LCP · CLS · TBT):

| Pantalla | Antes | Después |
| --- | --- | --- |
| Portada | 99 / 100 / 96 · 1,06 s · 0,002 · 100 ms | 100 / 100 / 100 · 1,24 s · 0,002 · 0 ms |
| Entrar | 100 / 100 / 96 · 1,09 s · 0 · 0 ms | 100 / 100 / 100 · 1,24 s · 0,001 · 0 ms |
| Clases | 100 / 100 / 96 · 1,69 s · 0 · 6 ms | 100 / 100 / 100 · 1,25 s · 0 · 0 ms |
| Panel (tutor) | 100 / 100 / 96 · 1,06 s · 0,001 · 26 ms | 100 / 100 / 100 · 1,07 s · 0,002 · 0 ms |
| Usuarios | 97 / 100 / 96 · 1,07 s · 0 · 0 ms | 100 / 100 / 100 · 1,08 s · 0 · 0 ms |
| Agenda | 93 / 100 / 96 · 1,06 s · 0 · 306 ms | 100 / 100 / 100 · 1,09 s · 0 · 19 ms |
| Tarea | 100 / 100 / 96 · 1,09 s · 0,036 · 0 ms | 100 / 100 / 100 · 1,09 s · 0,039 · 0 ms |
| Crear tarea | 100 / 98 / 96 · 1,20 s · 0,001 · 0 ms | 100 / 100 / 100 · 1,22 s · 0,003 · 0 ms |

Escritorio (portada, panel y agenda): 100 / 100 / 100 antes y después. Medido contra `runserver`,
sin compresión ni caché: los tiempos absolutos mejorarán con WhiteNoise o Caddy. El TBT varía entre
pasadas (se midió con dos Lighthouse a la vez). «Buenas prácticas» sube de 96 a 100 por el favicon.

## 7. Qué no se ha podido hacer y por qué

- **Leer la documentación oficial de la API de ARASAAC y probar contra ella.** El entorno de trabajo no
  tiene salida a `arasaac.org` ni a `api.arasaac.org`. Las rutas (`/v1/pictograms/es/search/<texto>` y
  `static.arasaac.org/pictograms/<id>/<id>_300.png`) son las del boceto v3 y la app anterior, y se
  pueden cambiar con `ARASAAC_URL_BUSQUEDA` y `ARASAAC_URL_IMAGEN`. La licencia CC BY-NC-SA se ha
  contrastado en fuentes secundarias (CATEDU, Aula Abierta de ARASAAC), no en `arasaac.org/terms-of-use`.
  **Alguien con Internet debe probar una búsqueda real antes de la demo.**
- **Descargar los pictogramas de la interfaz y el catálogo de avatares (Fase 4.6 y Fase 5).** Por lo mismo.
  Está el comando `descargar_pictogramas` (probado con red simulada) y el listado vacío. Portada, rejilla
  de entrada y avatares siguen con emojis y marcadores. De la Fase 5 solo está hecho el arreglo de las tildes.
- **Logotipo en SVG.** El boceto trae un PNG de 337×140; vectorizarlo sin el original lo deformaría. Va en WebP (6 kB).
- **Fase 2 completa.** Hechas la estructura común y las tres pantallas de tareas. El resto ya seguía el
  boceto en lo esencial; las diferencias que quedan están en el apartado 2.
- **Capturas con tema oscuro y alto contraste de todas las pantallas.** Solo comprobación con axe en las e2e existentes del perfil.
- **Pruebas con lector de pantalla, pulsador, tableta real y personas.**

## 8. Propuestas evaluadas

| Propuesta | Decisión | Motivo |
| --- | --- | --- |
| Migas de pan o «Volver» coherente | **Aplicada en parte (F1)** | «‹ Volver» pasa de la cabecera al contenido en 4 pantallas y el lateral marca la sección; migas no: más paradas de foco |
| Páginas 403, 404 y 500 accesibles | **Aplicada (F3)** | Barato y evita pantallas sin salida |
| Resumen de errores con enlaces | **Aplicada en tareas (F3)**; ya estaba en usuarios | Reutiliza `usuarios/_errores.html` |
| Foco y `aria-live` tras HTMX | **Aplicada en tareas (F4)**; ya estaba en agenda | Región `role="status"` fija y foco sin perderse |
| `forced-colors`, `prefers-contrast` | Propuesta | Riesgo bajo, coste medio: hay que revisar cada tarjeta con Windows en alto contraste |
| `prefers-reduced-motion` | Ya estaba | — |
| Cabeceras de seguridad, CSP, cookies, caducidad, `AXES_IPWARE_PROXY_COUNT` | Propuesta | Ya no hay código en línea, así que la CSP estricta es posible; hay que probarla con Caddy en la demo |
| WhiteNoise, `preload`, subconjunto de fuentes | Propuesta | Dependencia nueva: requiere justificarla; ganancia real solo en la demo |
| Hoja de impresión | **Aplicada lo mínimo (F1)**: se ocultan menú y «Salir» | La de listas y agenda, propuesta |
| Umbrales automáticos de Lighthouse y axe | Propuesta | axe ya corre en e2e; Lighthouse CI cuando vuelva GitHub Actions |
| Usabilidad cognitiva en agenda y tarea | Propuesta | Toca decisiones de producto (preguntas 2 y 6) |
| Foco al `h1` al cargar cada página | Descartada por ahora | En una web de varias páginas el navegador ya empieza arriba; saltaría la cabecera a quien usa teclado. Preguntar a las Gestoras de Accesibilidad |
| Iconos y flecha en las opciones del panel (B13) | Propuesta | Solo estética |
| Paginar o agrupar «Usuarios» y «Elegir mis estudiantes» | Propuesta | 25–35 paradas de foco |
| Guardar el menú abierto en `localStorage` | Descartada | En móvil debe empezar cerrado; en ordenador siempre se ve |

## 9. Preguntas para el equipo o el cliente

1. **ARASAAC es solo para uso no comercial (CC BY-NC-SA).** ¿Seguro que Despega nunca se va a vender ni a incluir en un servicio de pago? Además obliga a compartir igual lo derivado.
2. **¿Horario escolar y tareas van juntos en la misma pantalla del estudiante**, o separados como ahora (`/agenda/` y `/horario/mi-horario/`)? Pendiente desde la revisión con la profesora.
3. **Menú de tres barras.** Se ha puesto un botón con la palabra «Menú» (no tres barras) para todos los adultos en pantallas estrechas. La profesora lo recomendaba para profesionales; ¿vale para tutores, familiares y administración?
4. **¿El administrador puede crear y asignar tareas?** El diccionario de datos dice tutor, profesional o familiar; ahora el administrador recibe un 403.
5. **¿El catálogo de tareas es de todo el centro?** Ahora cualquier tutor, profesional o familiar ve y asigna las tareas creadas por otros.
6. **«Salir» del estudiante** está siempre a la vista en la cabecera. ¿Preocupa que lo pulsen sin querer? Alternativa: pedir confirmación.
7. **Avatares:** ¿catálogo de 30–40 pictogramas de animales y objetos, como se recomendó? Hace falta que alguien elija los pictogramas y sus números.
8. **Logotipo:** ¿alguien tiene el original en vectorial (SVG o AI)?
9. **Foco al título al cambiar de página** (lo hace el boceto, que es de una sola página): ¿lo quieren las Gestoras de Accesibilidad en la app?
10. **Límite del buscador de pictogramas:** 30 búsquedas por minuto y usuario. ¿Suficiente?

## 10. Qué debe revisar cada responsable

| Quién | Archivos tocados | Qué mirar |
| --- | --- | --- |
| **Úrsula** (tareas) | `apps/tareas/` entero (vistas, formularios, 3 plantillas + 3 parciales, pruebas), `static/css/tarea.css`, `static/js/tarea.js` | Es una reescritura: permisos por rol, estudiantes solo los propios, pasos, vista previa, pictogramas. Las dos pruebas de ARASAAC ahora comprueban la copia local |
| **Tomás** (agenda) | `agenda/dia.html`, `tarea.html`, `confirmar_fin.html` (solo se quita el bloque de cabecera); `tests/test_agenda_vistas.py` (una aserción) | El «Salir» nuevo y que la prueba de «no hay formularios» acepte ese |
| **Jorge** (perfil) | `apps/perfil/context_processors.py`, `perfil/estudiantes.html`, `editar.html`, `static/css/perfil.css` (3 tamaños de letra) | El cierre de sesión ya no está en el context processor |
| **Javi** (horario y consulta) | `horario/cargar.html`, `mi_horario.html`, `usuarios/mis_estudiantes.html`, `agenda_estudiante.html`, `apps/usuarios/consulta.py`, `_fecha_pedida` en `views.py` | «Volver» dentro del contenido; estado «Vencida»; fechas a un año como mucho |
| **Manu** (usuarios) | `apps/usuarios/navegacion.py` (nuevo, con `OPCIONES_POR_ROL`), `context_processors.py`, `middleware.py`, `views.py`, `altas.py`, plantillas de usuarios, `static/css/usuarios.css` (2 tamaños), `templates/`, `static/css/base.css`, `static/js/base.js`, `config/settings/base.py` | Estructura común, panel lateral y middleware de sesión |
