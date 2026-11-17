/*
 * Despega · Tareas del centro: anotar quién come (HU-05-04, boceto B61). Opcional: sin
 * JavaScript cada toque recarga la pantalla y funciona igual.
 *  1. Un toque en un compañero cambia su marca sin recargar (HTMX). El botón no se
 *     sustituye, así que el foco se queda en él y el barrido sigue donde estaba.
 *  2. Intro mantenido se repite solo: la repetición no cuenta como otro toque (si no,
 *     «Come» pasaría a «No come» sin querer). Un toque cada medio segundo como mucho.
 *  3. Si la respuesta no es la pantalla de la clase (sesión caducada, ya no es el
 *     encargado…), se recarga: lo mismo que pasaría sin JavaScript.
 */
(function () {
  "use strict";

  var ESPERA_MS = 500;
  var ultimo = 0;

  function esMarcar(evento) {
    var config = evento.detail && evento.detail.requestConfig;
    return Boolean(config && config.elt && config.elt.closest("[data-marcar]"));
  }

  document.addEventListener(
    "keydown",
    function (evento) {
      if ((evento.key === "Enter" || evento.key === " ") && evento.repeat) {
        evento.preventDefault();
      }
    },
    true
  );

  document.addEventListener(
    "submit",
    function (evento) {
      if (!evento.target.matches("[data-marcar]")) return;
      var ahora = Date.now();
      if (ahora - ultimo < ESPERA_MS) {
        evento.preventDefault();
        evento.stopImmediatePropagation();
        return;
      }
      ultimo = ahora;
    },
    true
  );

  document.addEventListener("htmx:beforeSwap", function (evento) {
    if (!esMarcar(evento)) return;
    var xhr = evento.detail.xhr;
    if (xhr.status !== 200 || xhr.responseText.indexOf('id="companeros"') === -1) {
      evento.detail.shouldSwap = false;
      evento.detail.isError = false;
      window.location.reload();
    }
  });

  document.addEventListener("htmx:sendError", function (evento) {
    var mensajes = document.getElementById("mensajes");
    if (!esMarcar(evento) || !mensajes) return;
    var aviso = document.createElement("div");
    aviso.className = "aviso-error aviso-error--estudiante";
    aviso.setAttribute("role", "alert");
    aviso.textContent = "No se ha podido guardar. Vuelve a tocar al compañero.";
    mensajes.replaceChildren(aviso);
  });
})();
