/* Despega · Estructura común (decisión 0003).
 * 1. Marca <html class="js"> antes de pintar: el CSS solo pliega el panel lateral si hay
 *    JavaScript para volver a abrirlo. Sin JavaScript el panel se ve siempre.
 * 2. Botón «Menú» de los adultos en pantallas estrechas: abre y cierra el panel lateral.
 *    No es un modal: no atrapa el foco. Escape lo cierra y devuelve el foco al botón.
 */
document.documentElement.classList.add("js");

document.addEventListener("DOMContentLoaded", function () {
  var boton = document.querySelector("[data-menu]");
  var panel = boton && document.getElementById(boton.getAttribute("aria-controls"));
  if (!boton || !panel) return;
  boton.hidden = false;

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
