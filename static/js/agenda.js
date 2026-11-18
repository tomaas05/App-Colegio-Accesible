/*
 * Despega · Pantallas de la agenda del estudiante (B06 y B07).
 * Cuatro cosas, todas opcionales: sin JavaScript las pantallas siguen funcionando.
 *  1. (El reloj pasó a base.js: ahora está en la barra de título de todas las pantallas.)
 *  2. «Escuchar la descripción» con la voz del dispositivo (HU-02-02). Solo suena al
 *     pulsarlo; el botón sigue oculto si el navegador no tiene voz.
 *  3. Confirmación de «Terminar» en un <dialog> (B08, RF2.5.1). Sin JavaScript, el
 *     enlace lleva a la misma pregunta en una página.
 *  4. Pasos (HU-02-05): tras «Hecho», el foco pasa al paso siguiente o a «Terminar».
 */
(function () {
  "use strict";

  // 1. El reloj de la barra de título lo lleva base.js (está en todas las pantallas del estudiante).

  // Dos cifras: lo usa el temporizador (4) para «24:58».
  function dos(n) {
    return n < 10 ? "0" + n : String(n);
  }

  // 2. Escuchar
  var boton = document.querySelector("[data-escuchar]");
  // Algunos navegadores de iPhone y iPad dicen que tienen voz y luego no suenan. Si pasa una
  // vez, el botón no se vuelve a ofrecer en esta sesión: mejor sin botón que con uno que no hace nada.
  var sinVoz = false;
  try {
    sinVoz = window.sessionStorage.getItem("despega-sin-voz") === "1";
  } catch (error) {
    sinVoz = false;
  }
  if (boton && "speechSynthesis" in window && !sinVoz) {
    var sintesis = window.speechSynthesis;
    var etiquetaInicial = boton.innerHTML;
    var sonando = false;
    // La frase que suena se guarda aquí: Safari la descarta a media lectura si nadie la guarda.
    var mensaje = null;
    // iPhone y iPad en modo silencio callan la voz del navegador aunque el volumen esté alto.
    // Un sonido mudo dentro de un <audio>, puesto al pulsar, hace que el sistema trate la voz
    // como un vídeo o una canción: suena con el volumen del dispositivo. No se oye nada más.
    var SILENCIO = "data:audio/wav;base64,UklGRkQDAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSADAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==";
    var mudo = null;
    var abrirSonido = function () {
      try {
        if (!mudo) {
          mudo = new Audio(SILENCIO);
          mudo.loop = true;
          mudo.setAttribute("playsinline", "");
        }
        var promesa = mudo.play();
        if (promesa && promesa.catch) {
          promesa.catch(function () {});
        }
      } catch (error) {
        mudo = null;
      }
    };
    var cerrarSonido = function () {
      if (mudo) {
        mudo.pause();
      }
    };
    var parar = function () {
      mensaje = null;
      sintesis.cancel();
      cerrarSonido();
      sonando = false;
      boton.innerHTML = etiquetaInicial;
    };
    // En iPhone y iPad la voz en español se elige a mano: con solo el idioma, a veces calla.
    var vozEnEspanol = function () {
      var voces = sintesis.getVoices ? sintesis.getVoices() : [];
      var espanol = voces.filter(function (voz) {
        return voz.lang && voz.lang.toLowerCase().replace("_", "-").indexOf("es") === 0;
      });
      var deEspana = espanol.filter(function (voz) {
        return voz.lang.toLowerCase().replace("_", "-") === "es-es";
      });
      // Apple trae, además de las voces normales (Mónica, Jorge, Marisol, Paulina), otras de
      // broma con el mismo idioma: se prefieren las normales.
      var normal = function (lista) {
        return lista.filter(function (voz) {
          return /m[oó]nica|jorge|marisol|paulina/i.test(voz.name || "");
        })[0];
      };
      return normal(deEspana) || normal(espanol) || deEspana[0] || espanol[0] || null;
    };
    // Safari carga las voces más tarde: pedirlas ya hace que estén al pulsar.
    vozEnEspanol();
    boton.hidden = false;
    boton.addEventListener("click", function () {
      if (sonando) {
        parar();
        return;
      }
      // Solo se corta si de verdad hay algo sonando: en iPhone y iPad, cancelar justo antes
      // de hablar hace que la frase nueva no llegue a sonar.
      if (sintesis.speaking || sintesis.pending) {
        sintesis.cancel();
      }
      var frase = new SpeechSynthesisUtterance(boton.dataset.texto);
      var voz = vozEnEspanol();
      frase.lang = voz ? voz.lang : "es-ES";
      if (voz) {
        frase.voice = voz;
      }
      var haEmpezado = false;
      frase.onstart = function () {
        haEmpezado = true;
      };
      // Cuatro segundos después, ni ha empezado ni está sonando: este navegador no lee.
      window.setTimeout(function () {
        if (mensaje !== frase || haEmpezado || sintesis.speaking) {
          return;
        }
        parar();
        boton.hidden = true;
        try {
          window.sessionStorage.setItem("despega-sin-voz", "1");
        } catch (error) {
          // Sin almacenamiento: el botón se esconde solo en esta página.
        }
      }, 4000);
      // El final o el error de una frase anterior no cambian el botón de la que suena ahora.
      frase.onend = frase.onerror = function () {
        if (mensaje === frase) {
          parar();
        }
      };
      abrirSonido();
      mensaje = frase;
      sonando = true;
      boton.textContent = boton.dataset.parar || "Parar";
      sintesis.speak(frase);
      // Safari deja a veces la voz en pausa al volver de otra pestaña.
      if (sintesis.paused) {
        sintesis.resume();
      }
    });
    window.addEventListener("pagehide", parar);
  }

  // 3. Confirmar. Se escucha en todo el documento (y no en cada enlace) porque «Terminar»
  // también puede aparecer sin recargar, al hacer el último paso (HU-02-05).
  document.addEventListener("click", function (evento) {
    var enlace = evento.target.closest("[data-confirmar]");
    if (!enlace) {
      return;
    }
    var dialogo = document.getElementById(enlace.dataset.confirmar);
    if (!dialogo || typeof dialogo.showModal !== "function") {
      return;
    }
    evento.preventDefault();
    dialogo.showModal();
  });

  // 4. Pasos (HU-02-05). Tras pulsar «Hecho», HTMX cambia la lista de pasos y el botón que
  // tenía el foco desaparece. El foco pasa al «Hecho» del paso siguiente o, si ya no
  // quedan, a «Terminar», como en el boceto. Así con teclado, pulsador o lector de
  // pantalla se sigue sin tener que buscar dónde se estaba.
  function esDeUnPaso(evento) {
    var config = evento.detail && evento.detail.requestConfig;
    return Boolean(config && config.elt && config.elt.hasAttribute("data-paso"));
  }

  // Tras mover el foco, un momento en el que «Hecho» no responde: así una pulsación larga
  // o con temblor no marca también el paso siguiente (cada paso, un «Hecho»).
  var ESPERA_MS = 500;
  var bloqueadoHasta = 0;

  document.addEventListener("htmx:afterSettle", function (evento) {
    if (!esDeUnPaso(evento)) {
      return;
    }
    var destino =
      document.querySelector("[data-paso] button") ||
      document.querySelector('[data-confirmar="confirmar-fin"]') ||
      document.getElementById("pasos");
    if (destino && destino !== document.activeElement) {
      destino.focus();
      bloqueadoHasta = Date.now() + ESPERA_MS;
    }
  });

  // Intro mantenido se repite solo: la repetición nunca cuenta como otra pulsación. Si no,
  // tras el último paso abriría «¿Has terminado?» y pulsaría «Sí» sin querer.
  document.addEventListener(
    "keydown",
    function (evento) {
      var activa = evento.key === "Enter" || evento.key === " ";
      if (activa && (evento.repeat || Date.now() < bloqueadoHasta)) {
        evento.preventDefault();
      }
    },
    true
  );
  document.addEventListener(
    "click",
    function (evento) {
      if (Date.now() < bloqueadoHasta && evento.target.closest("[data-paso], [data-confirmar]")) {
        evento.preventDefault();
        evento.stopPropagation();
      }
    },
    true
  );

  // Si la respuesta no es la pantalla de la tarea (sesión caducada, la tarea ya no toca
  // hoy, error del servidor…), no se cambia nada a medias: se recarga la página, que es
  // lo mismo que pasaría sin JavaScript.
  document.addEventListener("htmx:beforeSwap", function (evento) {
    if (!esDeUnPaso(evento)) {
      return;
    }
    var xhr = evento.detail.xhr;
    if (xhr.status !== 200 || xhr.responseText.indexOf('id="pasos"') === -1) {
      evento.detail.shouldSwap = false;
      evento.detail.isError = false;
      window.location.reload();
    }
  });

  // Sin conexión no hay respuesta: se avisa y el foco sigue en «Hecho» para reintentar.
  document.addEventListener("htmx:sendError", function (evento) {
    var mensajes = document.getElementById("mensajes");
    if (!esDeUnPaso(evento) || !mensajes) {
      return;
    }
    var aviso = document.createElement("div");
    aviso.className = "mensajes";
    aviso.setAttribute("role", "alert");
    aviso.textContent = "No se ha podido guardar. Vuelve a pulsar «Hecho».";
    mensajes.replaceChildren(aviso);
  });

    // 4. Temporizador de la tarea en curso (HU-07-01)
  var cajaTiempo = document.querySelector("[data-temporizador]");
  if (cajaTiempo) {
    var restanteInicial = parseInt(cajaTiempo.dataset.restanteSeg || "0", 10);
    var duracionTotal = Math.max(1, parseInt(cajaTiempo.dataset.duracionSeg || "1", 10));
    var instanteCarga = Date.now();
    var nodoTexto = cajaTiempo.querySelector("[data-temporizador-texto]");
    var nodoCorto = cajaTiempo.querySelector("[data-temporizador-corto]");
    var nodoReloj = cajaTiempo.querySelector("[data-temporizador-reloj]");
    var nodoBarra = cajaTiempo.querySelector("[data-temporizador-barra]");
    var nodoRelleno = cajaTiempo.querySelector("[data-temporizador-relleno]");
    var nodoArco = cajaTiempo.querySelector("[data-temporizador-arco]");
    var botonOcultar = cajaTiempo.querySelector("[data-ocultar-temporizador]");
    var cuerpoTiempo = cajaTiempo.querySelector("[data-temporizador-cuerpo]");
    var circunferencia = 226.19;

    var actualizarTemporizador = function () {
      var transcurridos = Math.floor((Date.now() - instanteCarga) / 1000);
      var quedan = Math.max(0, restanteInicial - transcurridos);
      var pct = Math.max(0, Math.min(100, Math.round((quedan * 100) / duracionTotal)));
      var minRestantes = quedan > 0 ? Math.ceil(quedan / 60) : 0;
      var mm = dos(Math.floor(quedan / 60));
      var ss = dos(quedan % 60);

      cajaTiempo.dataset.restanteActual = String(quedan);

      if (nodoTexto) {
        nodoTexto.textContent =
          quedan > 0 ? "Quedan " + minRestantes + " min" : "Se acabó el tiempo";
      }
      if (nodoCorto) {
        nodoCorto.textContent = minRestantes + " min";
      }
      if (nodoReloj) {
        nodoReloj.textContent = mm + ":" + ss;
      }
      if (nodoBarra) {
        nodoBarra.setAttribute("aria-valuenow", String(pct));
      }
      if (nodoRelleno) {
        nodoRelleno.style.width = pct + "%";
      }
      if (nodoArco) {
        var offset = ((circunferencia * (100 - pct)) / 100).toFixed(2);
        nodoArco.setAttribute("stroke-dashoffset", String(offset));
      }
    };

    actualizarTemporizador();
    window.setInterval(actualizarTemporizador, 1000);

    if (botonOcultar && cuerpoTiempo) {
      botonOcultar.addEventListener("click", function () {
        var ocultar = !cuerpoTiempo.hidden;
        cuerpoTiempo.hidden = ocultar;
        botonOcultar.setAttribute("aria-expanded", ocultar ? "false" : "true");
        botonOcultar.textContent = ocultar ? "Mostrar tiempo" : "Ocultar tiempo";
      });
    }
  }

})();
