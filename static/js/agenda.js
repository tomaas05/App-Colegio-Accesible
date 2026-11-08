/*
 * Despega · Pantallas de la agenda del estudiante (B06 y B07).
 * Tres cosas, todas opcionales: sin JavaScript las pantallas siguen funcionando.
 *  1. Reloj de la cabecera, puesto en hora cada segundo (RNF2.1.2).
 *  2. «Escuchar la descripción» con la voz del dispositivo (HU-02-02). Solo suena al
 *     pulsarlo; el botón sigue oculto si el navegador no tiene voz.
 *  3. Confirmación de «Terminar» en un <dialog> (B08, RF2.5.1). Sin JavaScript, el
 *     enlace lleva a la misma pregunta en una página.
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

  // 3. Confirmar
  document.querySelectorAll("[data-confirmar]").forEach(function (enlace) {
    var dialogo = document.getElementById(enlace.dataset.confirmar);
    if (!dialogo || typeof dialogo.showModal !== "function") {
      return;
    }
    enlace.addEventListener("click", function (evento) {
      evento.preventDefault();
      dialogo.showModal();
    });
  });
})();
