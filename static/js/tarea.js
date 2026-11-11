/* Despega · Crear tarea (Úrsula): pasos, buscador de pictogramas y vista previa.
 * Sin eventos en línea ni HTML escrito a mano: todo se engancha por atributos data-
 * y el texto del usuario se pone con textContent (nunca con innerHTML).
 * El navegador no habla con ARASAAC: la búsqueda la hace el servidor (decisión 0004).
 */
(function () {
  "use strict";
  var formulario = document.querySelector("[data-form-tarea]");
  if (!formulario) return;
  var lista = document.getElementById("contenedor-pasos");
  var total = document.getElementById("id_pasos-TOTAL_FORMS");
  var estado = formulario.querySelector("[data-pasos-estado]");
  var anadir = formulario.querySelector("[data-anadir-paso]");
  anadir.hidden = false;

  function pasosVisibles() {
    return Array.prototype.filter.call(lista.querySelectorAll("[data-paso]"), function (paso) {
      return !paso.hidden;
    });
  }

  /* Los pasos se numeran en el orden en que se ven; el servidor guarda ese orden. */
  function numerar() {
    pasosVisibles().forEach(function (paso, indice) {
      var numero = indice + 1;
      paso.querySelector("[data-paso-titulo]").textContent = "Paso " + numero;
      paso.querySelector('input[name$="-orden"]').value = numero;
      paso.querySelectorAll("[data-paso-nombre]").forEach(function (nombre) {
        nombre.textContent = "el paso " + numero;
      });
    });
    total.value = lista.querySelectorAll("[data-paso]").length;
  }

  function avisar(texto) {
    estado.textContent = texto;
  }

  /* HTMX pide un paso vacío: se le dice cuántos hay sin evaluar código (sin hx-vals js:). */
  anadir.addEventListener("htmx:configRequest", function (evento) {
    evento.detail.parameters.total_forms = lista.querySelectorAll("[data-paso]").length;
  });
  lista.addEventListener("htmx:afterSwap", function (evento) {
    if (evento.target !== lista) return;
    numerar();
    var nuevo = lista.lastElementChild;
    var primero = nuevo && nuevo.querySelector("textarea, input:not([type=hidden])");
    if (primero) primero.focus();
    avisar("Paso " + pasosVisibles().length + " añadido.");
  });

  lista.addEventListener("click", function (evento) {
    var boton = evento.target.closest("[data-paso-mover], [data-paso-quitar]");
    if (!boton) return;
    var paso = boton.closest("[data-paso]");
    if (boton.hasAttribute("data-paso-quitar")) {
      /* No se borra del HTML: el formulario de Django necesita el índice. Se marca DELETE. */
      paso.querySelector('input[name$="-DELETE"]').value = "on";
      paso.hidden = true;
      numerar();
      avisar("Paso quitado. Quedan " + pasosVisibles().length + ".");
      anadir.focus();
      return;
    }
    var visibles = pasosVisibles();
    var otro = visibles[visibles.indexOf(paso) + Number(boton.dataset.pasoMover)];
    if (!otro) return;
    if (boton.dataset.pasoMover === "-1") lista.insertBefore(paso, otro);
    else lista.insertBefore(otro, paso);
    numerar();
    boton.focus();
    avisar("Ahora es el paso " + (pasosVisibles().indexOf(paso) + 1) + ".");
  });

  /* Intro en el buscador busca; no envía el formulario entero. */
  formulario.addEventListener("keydown", function (evento) {
    var campo = evento.target.closest("[data-buscar-picto]");
    if (!campo || evento.key !== "Enter") return;
    evento.preventDefault();
    document.querySelector(campo.dataset.buscarPicto).click();
  });

  /* Elegir un pictograma y subir un archivo se excluyen: gana lo último que se toca. */
  formulario.addEventListener("change", function (evento) {
    var campo = evento.target;
    var grupo = campo.closest("fieldset.admin__tarjeta, [data-paso]");
    if (!grupo) return;
    if (campo.type === "file" && campo.value) {
      var ninguno = grupo.querySelector('.pictos input[type=radio][value=""]');
      if (ninguno) ninguno.checked = true;
    } else if (campo.type === "radio" && campo.closest(".pictos") && campo.value) {
      var archivo = grupo.querySelector("input[type=file]");
      if (archivo) archivo.value = "";
      /* La palabra del pictograma sirve de descripción si aún no hay ninguna. */
      var descripcion = grupo.querySelector('input[name$="descripcion_imagen"]');
      if (descripcion && !descripcion.value && campo.dataset.pictoNombre) {
        descripcion.value = campo.dataset.pictoNombre;
      }
    }
  });

  /* --- Vista previa antes de guardar --- */
  var dialogo = document.getElementById("vista-previa");
  var zona = dialogo && dialogo.querySelector("[data-vista-previa]");
  var temporales = [];

  function elemento(etiqueta, texto) {
    var nodo = document.createElement(etiqueta);
    if (texto) nodo.textContent = texto;
    return nodo;
  }
  function imagenDe(grupo) {
    var elegido = grupo.querySelector(".pictos input[type=radio]:checked");
    var archivo = grupo.querySelector("input[type=file]");
    var origen = "";
    if (elegido && elegido.value) origen = elegido.parentNode.querySelector("img").src;
    else if (archivo && archivo.files && archivo.files[0]) {
      origen = URL.createObjectURL(archivo.files[0]);
      temporales.push(origen);
    }
    if (!origen) return null;
    var imagen = document.createElement("img");
    imagen.src = origen;
    imagen.alt = "";
    imagen.width = 96;
    imagen.height = 96;
    return imagen;
  }
  function valor(selector, dentro) {
    var campo = (dentro || formulario).querySelector(selector);
    return campo ? campo.value.trim() : "";
  }
  function pintarVistaPrevia() {
    zona.textContent = "";
    zona.appendChild(elemento("h3", valor("#id_nombre") || "Sin nombre"));
    var imagen = imagenDe(formulario.querySelectorAll("fieldset.admin__tarjeta")[1]);
    if (imagen) zona.appendChild(imagen);
    if (valor("#id_descripcion")) zona.appendChild(elemento("p", valor("#id_descripcion")));
    var pasos = pasosVisibles();
    zona.appendChild(elemento("p", pasos.length ? "Pasos: " + pasos.length : "Sin pasos."));
    if (pasos.length) {
      var ol = elemento("ol");
      pasos.forEach(function (paso) {
        ol.appendChild(elemento("li", valor("textarea", paso) || "Sin descripción"));
      });
      zona.appendChild(ol);
    }
  }

  if (dialogo && typeof dialogo.showModal === "function") {
    formulario.querySelector("[data-revisar]").addEventListener("click", function (evento) {
      evento.preventDefault();
      pintarVistaPrevia();
      dialogo.showModal();
    });
    dialogo.querySelector("[data-confirmar-guardar]").addEventListener("click", function () {
      formulario.submit();
    });
    dialogo.addEventListener("close", function () {
      temporales.forEach(URL.revokeObjectURL);
      temporales = [];
    });
  }
  numerar();
})();
