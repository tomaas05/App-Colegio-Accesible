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
  document.addEventListener("htmx:afterSettle", function (evento) {
    var config = evento.detail && evento.detail.requestConfig;
    if (!config || !config.elt || !config.elt.hasAttribute("data-paso")) {
      return;
    }
    var destino =
      document.querySelector("[data-paso] button") ||
      document.querySelector("[data-confirmar]") ||
      document.getElementById("pasos");
    if (destino && destino !== document.activeElement) {
      destino.focus();
    }
  });
})();
