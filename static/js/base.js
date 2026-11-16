/* Despega · Estructura común (decisión 0003).
 * 1. Marca <html class="js"> antes de pintar: el CSS solo pliega el panel lateral si hay
 *    JavaScript para volver a abrirlo. Sin JavaScript el panel se ve siempre.
 * 2. Botón «Menú» de los adultos en pantallas estrechas: abre y cierra el panel lateral.
 *    No es un modal: no atrapa el foco. Escape lo cierra y devuelve el foco al botón.
 * 3. Reloj de la barra de título del estudiante, puesto en hora cada segundo (RNF2.1.2).
 * 4. Los plegables con data-abrir-ancho empiezan abiertos en pantallas anchas.
 */
document.documentElement.classList.add("js");

document.addEventListener("DOMContentLoaded", function () {
  var relojes = document.querySelectorAll("[data-reloj]");
  function dos(n) {
    return n < 10 ? "0" + n : String(n);
  }
  function tic() {
    var d = new Date();
    var texto = dos(d.getHours()) + ":" + dos(d.getMinutes());
    relojes.forEach(function (r) {
      if (r.textContent !== texto) r.textContent = texto;
    });
  }
  if (relojes.length) {
    tic();
    window.setInterval(tic, 1000);
  }

  // Plegables que en pantallas anchas empiezan abiertos (buscar y filtrar).
  if (window.matchMedia && window.matchMedia("(min-width: 48rem)").matches) {
    document.querySelectorAll("details[data-abrir-ancho]").forEach(function (d) {
      d.open = true;
    });
  }

  var boton = document.querySelector("[data-menu]");
  var panel = boton && document.getElementById(boton.getAttribute("aria-controls"));
  if (!boton || !panel) return;

  function abrir(si) {
    boton.setAttribute("aria-expanded", si ? "true" : "false");
    panel.classList.toggle("lateral--abierto", si);
  }
  boton.addEventListener("click", function () {
    abrir(boton.getAttribute("aria-expanded") !== "true");
  });
  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape" || boton.getAttribute("aria-expanded") !== "true") return;
    var dentro = panel.contains(document.activeElement) || document.activeElement === boton;
    abrir(false);
    if (dentro) boton.focus();
  });
});
