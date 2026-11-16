/*
 * Despega · Perfil visual por categorías (HU-04-01, decisión 0005).
 * Sin JavaScript el formulario se ve entero y se guarda igual. Con JavaScript:
 *  1. Dos pasos: primero las categorías (Tema, Colores, Letra…) y, al pulsar una, sus
 *     opciones. «‹ Categorías» vuelve al paso 1. Nunca hay que desplazarse.
 *  2. No hay vista previa aparte: la propia tarjeta de configuración se pinta con lo que se
 *     va eligiendo (colores, letra y tamaño de botones), con los mismos atributos data-*
 *     que lleva la pantalla del estudiante.
 *  3. Nada se guarda hasta pulsar «Guardar». Si hay cambios sin guardar se dice en el pie y,
 *     al intentar salir de la pantalla, se pregunta qué hacer.
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-perfil]");
  if (!form) return;
  var tarjeta = form.querySelector("[data-perfil-tarjeta]");
  var inicio = form.querySelector("[data-perfil-inicio]");
  var paneles = form.querySelectorAll("[data-panel]");
  var atras = form.querySelector("[data-perfil-atras]");
  var pendiente = form.querySelector("[data-perfil-pendiente]");
  var dialogo = document.getElementById("perfil-salir");
  var abierta = null; // botón de la categoría abierta, para devolverle el foco

  // Campo del formulario → atributo de la tarjeta.
  var ATRIBUTOS = {
    tema: "tema",
    paleta: "paleta",
    tipo_letra: "fuente",
    tamano_letra: "letra",
    tamano_botones: "botones",
  };

  function elegido(nombre) {
    return form.querySelector('input[name="' + nombre + '"]:checked');
  }
  function texto(campo) {
    var etiqueta = campo && campo.closest("label");
    return etiqueta ? etiqueta.textContent.trim() : "";
  }

  // 2. La tarjeta se pinta con lo elegido y las categorías dicen qué hay puesto.
  function pintar() {
    Object.keys(ATRIBUTOS).forEach(function (nombre) {
      var campo = elegido(nombre);
      if (campo) tarjeta.dataset[ATRIBUTOS[nombre]] = campo.value;
    });
    form.querySelectorAll("[data-valor-de]").forEach(function (destino) {
      var nombre = destino.dataset.valorDe;
      var campo = form.querySelector('input[name="' + nombre + '"]');
      if (campo && campo.type === "checkbox") {
        destino.textContent = campo.checked ? destino.dataset.si : destino.dataset.no;
      } else if (elegido(nombre)) {
        destino.textContent = texto(elegido(nombre));
      }
    });
    if (window.Despega && window.Despega.paginar) window.Despega.paginar.reajustar();
  }

  // 3. Cambios sin guardar: se compara con lo que había al abrir la pantalla.
  function foto() {
    var partes = [];
    new FormData(form).forEach(function (valor, clave) {
      if (clave !== "csrfmiddlewaretoken" && clave !== "siguiente") partes.push(clave + "=" + valor);
    });
    return partes.sort().join("&");
  }
  var original = foto();
  function hayCambios() {
    return foto() !== original;
  }
  function avisar() {
    if (pendiente) pendiente.textContent = hayCambios() ? "● Hay cambios sin guardar." : "";
  }

  form.addEventListener("change", function () {
    pintar();
    avisar();
  });

  // 1. Categorías y opciones.
  function mostrar(clave, foco) {
    inicio.hidden = Boolean(clave);
    atras.hidden = !clave;
    paneles.forEach(function (panel) {
      panel.hidden = panel.dataset.panel !== clave;
    });
    if (window.Despega && window.Despega.paginar) window.Despega.paginar.reajustar();
    if (!foco) return;
    if (clave) {
      var panel = form.querySelector('[data-panel="' + clave + '"]');
      var destino = panel.querySelector("input:checked") || panel.querySelector("input");
      if (destino) destino.focus();
    } else if (abierta) {
      // La categoría puede estar en otra página del paginador: primero se enseña.
      if (window.Despega && window.Despega.paginar) window.Despega.paginar.mostrar(abierta);
      abierta.focus();
    }
  }
  inicio.addEventListener("click", function (evento) {
    var boton = evento.target.closest("[data-abrir]");
    if (!boton) return;
    abierta = boton;
    mostrar(boton.dataset.abrir, true);
  });
  atras.addEventListener("click", function () {
    mostrar("", true);
  });

  // Si el servidor devuelve errores, se abre la categoría del primer campo con error.
  var conError = form.querySelector("[data-panel] [aria-invalid='true'], [data-panel] .errorlist");
  mostrar(conError ? conError.closest("[data-panel]").dataset.panel : "", false);
  pintar();

  // Salir con cambios sin guardar. Los enlaces de la página preguntan en un diálogo propio;
  // cerrar la pestaña o recargar, con el aviso del navegador.
  var saliendo = false;
  var destino = "";
  form.addEventListener("submit", function () {
    saliendo = true;
  });
  window.addEventListener("beforeunload", function (evento) {
    if (saliendo || !hayCambios()) return;
    evento.preventDefault();
    evento.returnValue = "";
  });
  document.addEventListener("click", function (evento) {
    var enlace = evento.target.closest("a[href]");
    if (!enlace || !hayCambios() || enlace.target === "_blank") return;
    if (enlace.getAttribute("href").charAt(0) === "#") return;
    if (!dialogo || typeof dialogo.showModal !== "function") return; // queda el aviso del navegador
    evento.preventDefault();
    destino = enlace.href;
    dialogo.showModal();
  });
  if (dialogo) {
    dialogo.addEventListener("click", function (evento) {
      var boton = evento.target.closest("[data-salir]");
      if (!boton) return;
      if (boton.dataset.salir === "guardar") {
        form.elements.siguiente.value = destino;
        saliendo = true;
        form.submit();
      } else if (boton.dataset.salir === "descartar") {
        saliendo = true;
        window.location.href = destino;
      } else {
        dialogo.close();
      }
    });
  }
})();
