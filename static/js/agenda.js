/*
 * Despega · Pantallas de la agenda del estudiante (B06 y B07).
 * Cuatro cosas, todas opcionales: sin JavaScript las pantallas siguen funcionando.
 *  1. Reloj de la cabecera, puesto en hora cada segundo (RNF2.1.2).
 *  2. «Escuchar la descripción» con la voz del dispositivo (HU-02-02). Solo suena al
 *     pulsarlo; el botón sigue oculto si el navegador no tiene voz.
 *  3. Confirmación de «Terminar» en un <dialog> (B08, RF2.5.1). Sin JavaScript, el
 *     enlace lleva a la misma pregunta en una página.
 *  4. Pasos (HU-02-05): tras «Hecho», el foco pasa al paso siguiente o a «Terminar».
 */
(function () {
  "use strict";

  // 1. Reloj
  var relojes = document.querySelectorAll("[data-reloj]");
  function dos(n) {
    return n < 10 ? "0" + n : String(n);
  }
  function tic() {
    var d = new Date();
    var texto = dos(d.getHours()) + ":" + dos(d.getMinutes());
    relojes.forEach(function (r) {
      if (r.textContent !== texto) {
        r.textContent = texto;
      }
    });
  }
  if (relojes.length) {
    tic();
    window.setInterval(tic, 1000);
  }

  // 2. Escuchar
  var boton = document.querySelector("[data-escuchar]");
  if (boton && "speechSynthesis" in window) {
    var etiquetaInicial = boton.innerHTML;
    var sonando = false;
    var parar = function () {
      window.speechSynthesis.cancel();
      sonando = false;
      boton.innerHTML = etiquetaInicial;
    };
    boton.hidden = false;
    boton.addEventListener("click", function () {
      if (sonando) {
        parar();
        return;
      }
      var mensaje = new SpeechSynthesisUtterance(boton.dataset.texto);
      mensaje.lang = "es-ES";
      mensaje.onend = parar;
      mensaje.onerror = parar;
      window.speechSynthesis.cancel();
      sonando = true;
      boton.textContent = boton.dataset.parar || "Parar";
      window.speechSynthesis.speak(mensaje);
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
      document.querySelector("[data-confirmar]") ||
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
})();
