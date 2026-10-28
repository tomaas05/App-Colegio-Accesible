# Despega · Contexto del mockup interactivo (para pasar a nuevas sesiones)

## Qué estamos haciendo
Mockup interactivo en HTML de la app Despega (agenda accesible, Colegio Purísima Concepción), pantalla a pantalla a partir de los bocetos a mano del usuario. Solo estructura y un estilo ligero. Las pantallas de otro asistente de IA (despega_prototipo_navegable.html) son solo referencia; manda el boceto del usuario.

## Archivos
- `despega_mockup.html`: TODAS las pantallas en un solo archivo (una `<main id="...">` por pantalla, navegación con `ir(id)`), con logo embebido. Sin dependencias salvo Google Fonts. Antes se llamaba despega_01_bienvenida.html.
- Logos originales: Imagotipo.jpeg (cohete + «Despega») e icono_app.jpeg (icono de app). El imagotipo va en la barra superior y el icono como favicon.

## Decisiones de diseño
- Paleta (códigos aproximados, el manual no los trae): petróleo #0B3C49, verde azulado oscuro #1F6F6B, verde azulado #3AA39A, naranja #F28C28 (solo adorno), menta #E3F4EF, texto #1E2B2F, gris #5B6B70, foco #0B57D0.
- Tipografía: Nunito 800 para títulos y botones, Open Sans para texto; fallback Arial.
- Botones redondeados (radio 1.5rem en tarjetas, 999px en botones pequeños). Borde petróleo, fondo menta.
- Sin modo oscuro por ahora. Sin botón de escuchar por ahora.
- Tamaño de letra ajustable en la barra superior: 16 / 20 / 24 / 32 px (RF4.1.2). Todo en rem; se guarda el último valor (localStorage con try/catch).
- Lenguaje claro y literal: nada de metáforas ni referencias espaciales en los textos que lee el estudiante (el título es «¿Quién eres?»). El tema de la nave vive solo en el logo.

## Reglas de accesibilidad que aplicar en todas las pantallas
- HTML semántico: `button`, `nav`, `main`, `h1`, `label`, listas. Foco visible (4px) y navegación por teclado. Al cambiar de pantalla, el foco va al `h1`.
- Elementos táctiles de al menos 48 px; contraste de texto 4,5:1; el color nunca es la única señal.
- Cada pictograma lleva texto al lado y alternativa accesible (`role="img"` + `aria-label`).
- Sin ventanas emergentes salvo las 3 permitidas (terminar / «No puedo hacerla», cancelar tarea, eliminar cuenta). Sin audio ni animación automáticos.
- Formatos objetivo: móvil vertical 360×640, tablet horizontal 1280×800 (y ordenador 1366×768) sin scroll horizontal.
- Navegación entre pantallas del mockup: un `<main id="...">` por pantalla y la función `ir(id)`.

## Pantalla 1 (hecha): Bienvenida / tipo de usuario
Título «¿Quién eres?». Dos opciones del mismo tamaño, centradas: Estudiante y Adulto (pictograma + texto). En móvil se apilan. Estudiante → «Elige tu clase» → avatar, sin contraseña (RF1.3.1). Adulto → usuario y contraseña (RF1.3.3). Los pictogramas son cajas con X, pendientes de ARASAAC.

## Pantalla 2 (hecha): Elegir clase y avatar (login del estudiante)
Boceto: barra de pestañas de clase arriba («Clase A», «Clase B»…), línea separadora y rejilla de tarjetas (avatar + nombre + primer apellido). Nota del usuario: adaptar el tamaño para que quepan todos en una pantalla; hay unos 80 alumnos en total (lo leí como «80?»), así que cada clase es pequeña.
- Título «¿Cuál eres tú?». Pestañas con `role="tablist"` y flechas del teclado. Un toque en la tarjeta entra en el menú del estudiante, sin contraseña.
- El tamaño de las tarjetas se calcula en JS (`ajustar()`) para que quepa toda la clase; mínimo 5 rem y máximo 11 rem. Si no cabe (móvil o letra de 32 px), la pantalla se desplaza en vertical y el texto nunca se corta.
- Avatares: emojis de relleno, sin fotos. Datos ficticios (clases A, B, C con 12, 9 y 14 alumnos).
- Pendiente: el estudiante podrá cambiar su avatar desde el perfil en cualquier momento, y habrá que decidir de dónde salen los avatares (catálogo propio o API). Ojo con RNF1.1.2: ningún dato personal (nombre, clase) puede enviarse a un servicio externo, así que habría que pedir avatares genéricos o usar un catálogo local.

## Pantalla 3 (hecha): Login de adultos
Login clásico (usuario + contraseña) para tutor, profesional, familiar y administrador. Etiquetas visibles, botón Mostrar/Ocultar contraseña, `autocomplete` correcto.
- Campo vacío: no se envía, se marca el campo (`aria-invalid`) y el foco va al primero que falta (HU-01-07).
- Datos incorrectos: aviso con texto y pictograma «Los datos no coinciden con una cuenta existente» (RF1.3.4). Tras 5 fallos seguidos, bloqueo de 5 minutos (RNF1.2.3); en el mockup se guarda en memoria.
- Al entrar lleva al panel del rol (pantalla de relleno por ahora, con «Hola, nombre», el rol y qué contendrá). Botón «Salir» vuelve al inicio.
- Cuentas de prueba (ficticias), contraseña `despega`: mperez (tutor), lgomez (profesional), cruiz (familiar), admin (administrador).

## Pantallas de relleno
«Menú principal del estudiante» (muestra «Hola, nombre») y el panel de cada rol de adulto (una sola pantalla `panel` que cambia según la cuenta). Sustituir cuando lleguen sus bocetos; la pantalla `panel` se dividirá en una por rol.

## Pantallas siguientes
Pendientes de recibir el boceto del usuario.
