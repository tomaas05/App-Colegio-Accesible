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
