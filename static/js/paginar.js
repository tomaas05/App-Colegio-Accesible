/*
 * Despega · Paginar en lugar de desplazarse (decisión 0005).
 *
 * Una lista con data-paginar enseña solo los elementos que caben en su zona (.encaja) y el
 * resto pasa a otras páginas, con los botones «Anterior / Siguiente» de _paginador.html.
 * Sirve igual para una rejilla de avatares, la línea de tiempo de la agenda, una tabla o los
 * pasos de un formulario largo: así ninguna pantalla necesita desplazamiento.
 *
 *   <div class="encaja">
 *     <ul id="lista" data-paginar> … </ul>            los hijos son los elementos
 *   </div>
 *   {% include "_paginador.html" with de="lista" %}
 *
 * Atributos de la lista:
 *   data-max="6"          como mucho 6 por página, aunque quepan más (perfil del estudiante)
 *   data-por-pagina="1"   tamaño fijo, sin medir: un formulario por pasos
 *   data-estado="Paso {n} de {total}"   texto del centro (por defecto «Página {n} de {total}»)
 *   data-foco="titulo"    al cambiar de página el foco va al título del elemento (pasos)
 *   data-items=".opcion"  los elementos no son los hijos directos, sino lo que diga el selector
 *   data-pag-variable     elementos de tamaños distintos (los bloques de un formulario): cada
 *                         página lleva los que caben, no un número fijo
 *   data-pag-desplaza="(max-width: 47.99rem)"   solo en pantallas de adulto: mientras se cumpla
 *                         esa condición la lista se ve entera y la pantalla se desplaza (una
 *                         lista de cuentas en el móvil). Las pantallas del estudiante nunca.
 * En un elemento: aria-current o data-pag-inicio para empezar en su página (la tarea de
 * ahora); data-titulo para añadir su nombre al texto del centro; data-pag-fuera (en él o en
 * un antecesor) para que no cuente (un paso quitado, la sección de otro rol).
 * Fuera de la lista: data-solo-ultima="lista" (solo en la última página, p. ej. «Guardar»)
 * y data-solo-primera="lista".
 * Listas que el servidor ya trae por páginas (Usuarios): data-url-anterior y data-url-siguiente
 * en el paginador hacen que, al llegar al principio o al final, los botones pidan la página
 * anterior o siguiente al servidor; data-total y data-desde permiten «{desde} a {hasta} de {de}».
 *
 * Sin JavaScript no se oculta nada: la lista se ve entera y la página se desplaza.
 */
(function () {
  "use strict";

  var listas = [];

  // Los elementos son los hijos de la lista o, con data-items="selector", lo que diga el selector.
  function hijos(lista) {
    var todos = lista.dataset.items ? lista.querySelectorAll(lista.dataset.items) : lista.children;
    return Array.prototype.filter.call(todos, function (e) {
      return !e.closest("[data-pag-fuera]");
    });
  }

  // De qué elemento a cuál va una página, y en qué página está un elemento.
  function rango(e, pagina) {
    if (e.cortes) return [e.cortes[pagina], e.cortes[pagina + 1]];
    return [pagina * e.por, pagina * e.por + e.por];
  }
  function paginaDe(e, indice) {
    if (!e.cortes) return Math.floor(indice / e.por);
    for (var p = 0; p < e.cortes.length - 1; p++) {
      if (indice < e.cortes[p + 1]) return p;
    }
    return Math.max(0, e.cortes.length - 2);
  }

  function caben(zona) {
    return zona.scrollHeight <= zona.clientHeight + 1 && zona.scrollWidth <= zona.clientWidth + 1;
  }

  function buscar(lista) {
    for (var i = 0; i < listas.length; i++) {
      if (listas[i].lista === lista) return listas[i];
    }
    return null;
  }

  function preparar(lista) {
    if (!lista.id || buscar(lista)) return;
    // El paginador es opcional: sin él solo se enseña la página inicial (el paso que toca).
    var nav = document.querySelector('[data-paginador="' + lista.id + '"]') || document.createElement("nav");
    var e = {
      lista: lista,
      nav: nav,
      zona: lista.closest(".encaja") || lista.parentElement,
      estado: nav.querySelector("[data-pag-estado]"),
      botones: nav.querySelectorAll("[data-pag]"),
      fijo: parseInt(lista.dataset.porPagina, 10) || 0,
      variable: lista.hasAttribute("data-pag-variable"),
      cortes: null,
      max: parseInt(lista.dataset.max, 10) || Infinity,
      plantilla: lista.dataset.estado || "Página {n} de {total}",
      por: 1,
      pagina: 0,
      primero: -1, // índice del primer elemento visible: se conserva al cambiar de tamaño
      ancho: 0,
      alto: 0,
    };
    listas.push(e);

    nav.addEventListener("click", function (evento) {
      var boton = evento.target.closest("[data-pag]");
      if (!boton || boton.disabled) return;
      ir(e, e.pagina + parseInt(boton.dataset.pag, 10), boton);
    });

    // Al añadir o quitar elementos (un paso nuevo, resultados de una búsqueda) se vuelve a medir.
    new MutationObserver(function () {
      programar(e, true);
    }).observe(lista, { childList: true });

    if ("ResizeObserver" in window) {
      new ResizeObserver(function () {
        var z = e.zona;
        if (z.clientWidth !== e.ancho || z.clientHeight !== e.alto) programar(e);
      }).observe(e.zona);
    }
    ajustar(e, true);
  }

  var pendientes = [];
  function programar(e, alFinal) {
    e.alFinal = e.alFinal || Boolean(alFinal && e.lista.hasAttribute("data-pag-seguir"));
    if (pendientes.indexOf(e) >= 0) return;
    pendientes.push(e);
    window.requestAnimationFrame(function () {
      var cola = pendientes;
      pendientes = [];
      cola.forEach(function (uno) {
        ajustar(uno, false);
      });
    });
  }

  // Si los dos botones y el texto no caben en una fila (letra de 32 px en un móvil), el texto
  // sube a su propia fila: los botones nunca se salen de la pantalla.
  function colocarNav(e) {
    e.nav.classList.remove("paginador--apilado");
    if (!e.nav.hidden && e.nav.scrollWidth > e.nav.clientWidth + 1) e.nav.classList.add("paginador--apilado");
  }

  // Cuántos elementos caben: se enseñan todos y se van quitando del final hasta que entren.
  function ajustar(e, inicial) {
    var items = hijos(e.lista);
    var total = items.length;
    var zona = e.zona;
    zona.classList.remove("sin-encaje");

    if (inicial || e.primero < 0) {
      e.primero = 0;
      for (var i = 0; i < total; i++) {
        if (items[i].matches("[aria-current], [data-pag-inicio]") || items[i].querySelector("[aria-current], [data-pag-inicio], [aria-invalid='true'], .campo__error, .errorlist")) {
          e.primero = i;
          break;
        }
      }
    }
    // «#fin» en la dirección: se llega de la página siguiente del servidor pulsando «Anterior».
    if (e.alFinal || (inicial && window.location.hash === "#fin" && e.nav.dataset.urlSiguiente !== undefined)) {
      e.primero = Math.max(0, total - 1);
      e.alFinal = false;
    }

    var por;
    e.cortes = null;
    if (e.lista.dataset.pagDesplaza && window.matchMedia(e.lista.dataset.pagDesplaza).matches) {
      // Lista de adultos en el móvil: entera, y se desplaza <main> (como cuando no cabe ni uno).
      items.forEach(function (it) {
        it.hidden = false;
      });
      por = Math.max(1, total);
      zona.classList.add("sin-encaje");
    } else if (e.fijo) {
      por = e.fijo;
      e.nav.hidden = total <= por;
    } else if (e.variable) {
      // Tamaños distintos: primero se prueba con todo; si no cabe, se llena página a página.
      items.forEach(function (it) {
        it.hidden = false;
      });
      e.nav.hidden = true;
      var cortes = [0, total];
      if (total > 1 && !caben(zona)) {
        e.nav.hidden = false;
        if (e.estado && !e.estado.textContent) e.estado.textContent = e.plantilla.replace("{n}", 1).replace("{total}", total);
        colocarNav(e);
        cortes = [0];
        var k = 0;
        var estrecho = false;
        while (k < total) {
          items.forEach(function (it, i) {
            it.hidden = i !== k;
          });
          if (!caben(zona)) estrecho = true;
          var j = k + 1;
          while (j < total && j - k < e.max) {
            items[j].hidden = false;
            if (!caben(zona)) {
              items[j].hidden = true;
              break;
            }
            j++;
          }
          cortes.push(j);
          k = j;
        }
        if (estrecho) zona.classList.add("sin-encaje"); // un bloque no cabe solo: se desplaza <main>
      } else if (!caben(zona)) {
        zona.classList.add("sin-encaje");
      }
      e.cortes = cortes;
      por = 1;
    } else {
      var n = Math.min(total, e.max);
      items.forEach(function (it, i) {
        it.hidden = i >= n;
      });
      e.nav.hidden = true;
      if (n < total || !caben(zona)) {
        e.nav.hidden = total <= 1;
        if (e.estado && !e.estado.textContent) e.estado.textContent = e.plantilla.replace("{n}", 1).replace("{total}", total);
        colocarNav(e);
        while (n > 1 && !caben(zona)) {
          n--;
          items[n].hidden = true;
        }
        if (!caben(zona)) zona.classList.add("sin-encaje"); // ni uno cabe: se desplaza <main>
      }
      por = Math.max(1, n);
    }
    // Al volver a repartir (llegan resultados, cambia el tamaño), la pantalla que se ve es la
    // del elemento que tiene el foco: así el foco nunca se queda en algo escondido.
    var activo = document.activeElement;
    if (!inicial && activo && activo !== document.body && e.lista.contains(activo)) {
      for (var a = 0; a < total; a++) {
        if (items[a].contains(activo)) {
          e.primero = a;
          break;
        }
      }
    }
    e.por = por;
    e.total = total;
    e.paginas = e.cortes ? e.cortes.length - 1 : Math.max(1, Math.ceil(total / por));
    e.pagina = Math.min(e.paginas - 1, paginaDe(e, e.primero));
    e.ancho = zona.clientWidth;
    e.alto = zona.clientHeight;
    pintar(e, items);
  }

  function pintar(e, items) {
    items = items || hijos(e.lista);
    var tramo = rango(e, e.pagina);
    var desde = tramo[0];
    var hasta = tramo[1];
    items.forEach(function (it, i) {
      it.hidden = i < desde || i >= hasta;
    });
    e.primero = desde;
    var hayMasEnElServidor = Boolean(e.nav.dataset.urlAnterior || e.nav.dataset.urlSiguiente);
    e.nav.hidden = e.paginas <= 1 && !hayMasEnElServidor;
    e.botones.forEach(function (b) {
      var d = parseInt(b.dataset.pag, 10);
      var url = d < 0 ? e.nav.dataset.urlAnterior : e.nav.dataset.urlSiguiente;
      b.disabled = (d < 0 ? e.pagina === 0 : e.pagina >= e.paginas - 1) && !url;
    });
    if (e.estado) {
      var actual = items[desde];
      var titulo = actual && actual.dataset.titulo;
      // «Página 2 de 3»: la primera palabra se esconde a la vista en el móvil (sigue leyéndose).
      var base = parseInt(e.nav.dataset.desde, 10) || 0;
      // Con un solo elemento a la vista, «3 de 15» en lugar de «3 a 3 de 15».
      var plantilla = hasta - desde === 1 ? e.plantilla.replace("{desde} a {hasta}", "{desde}") : e.plantilla;
      var texto =
        plantilla
          .replace("{n}", e.pagina + 1)
          .replace("{total}", e.paginas)
          .replace("{desde}", base + desde + 1)
          .replace("{hasta}", base + Math.min(hasta, items.length))
          .replace("{de}", e.nav.dataset.total || items.length) + (titulo ? ": " + titulo : "");
      // La palabra de delante («Página», «Franjas») se esconde a la vista en el móvil.
      var marcas = [plantilla.indexOf("{n}"), plantilla.indexOf("{desde}")].filter(function (i) {
        return i >= 0;
      });
      var corte = marcas.length ? Math.min.apply(null, marcas) : -1;
      e.estado.textContent = "";
      if (corte > 0) {
        var palabra = document.createElement("span");
        palabra.className = "paginador__palabra";
        palabra.textContent = texto.slice(0, corte);
        e.estado.appendChild(palabra);
      }
      e.estado.appendChild(document.createTextNode(texto.slice(Math.max(0, corte))));
    }
    var ultima = e.pagina >= e.paginas - 1;
    marcar("data-solo-ultima", e.lista.id, !ultima);
    marcar("data-no-ultima", e.lista.id, ultima);
    marcar("data-solo-primera", e.lista.id, e.pagina !== 0);
    e.lista.dataset.pagina = e.pagina + 1;
    e.lista.dataset.paginas = e.paginas;
    e.lista.dispatchEvent(
      new CustomEvent("paginar:cambio", { bubbles: true, detail: { pagina: e.pagina, paginas: e.paginas, por: e.por } })
    );
  }

  function marcar(atributo, id, ocultar) {
    document.querySelectorAll("[" + atributo + '="' + id + '"]').forEach(function (el) {
      el.hidden = ocultar;
    });
  }

  function ir(e, pagina, boton) {
    // En los extremos, si el servidor tiene más páginas, se le pide la anterior o la siguiente.
    if (pagina < 0 && e.nav.dataset.urlAnterior) {
      window.location.href = e.nav.dataset.urlAnterior;
      return;
    }
    if (pagina >= e.paginas && e.nav.dataset.urlSiguiente) {
      window.location.href = e.nav.dataset.urlSiguiente;
      return;
    }
    pagina = Math.max(0, Math.min(e.paginas - 1, pagina));
    if (pagina === e.pagina) return;
    e.pagina = pagina;
    // Desde ahora el texto del centro se anuncia al lector de pantalla (no al cargar).
    if (e.estado) e.estado.setAttribute("role", "status");
    pintar(e);
    if (e.lista.dataset.foco === "titulo") {
      var item = hijos(e.lista)[rango(e, e.pagina)[0]];
      var titulo = item && (item.querySelector("legend, h2, h3, [data-pag-titulo]") || item);
      if (titulo) {
        titulo.setAttribute("tabindex", "-1");
        titulo.focus();
      }
    } else if (boton && boton.disabled) {
      // El botón pulsado ya no sirve (primera o última página): el foco pasa al otro.
      var otro = e.nav.querySelector("[data-pag]:not(:disabled)");
      if (otro) otro.focus();
    }
  }

  // Enseña la página en la que está un elemento (un campo con error, el destino de un enlace).
  function mostrar(el) {
    var cambiado = false;
    listas.forEach(function (e) {
      if (!e.lista.contains(el) || el === e.lista) return;
      var items = hijos(e.lista);
      for (var i = 0; i < items.length; i++) {
        if (items[i].contains(el)) {
          var pagina = paginaDe(e, i);
          if (pagina !== e.pagina) {
            e.pagina = pagina;
            pintar(e, items);
            cambiado = true;
          }
          break;
        }
      }
    });
    return cambiado;
  }

  // Enlaces a un punto de la misma página (el resumen de errores): primero se enseña su página.
  document.addEventListener("click", function (evento) {
    var enlace = evento.target.closest('a[href^="#"]');
    if (!enlace || enlace.getAttribute("href").length < 2) return;
    var destino = document.getElementById(decodeURIComponent(enlace.getAttribute("href").slice(1)));
    if (destino && destino.closest("[hidden]")) mostrar(destino);
  });

  function todas(raiz) {
    (raiz || document).querySelectorAll("[data-paginar]").forEach(preparar);
  }
  function reajustar() {
    listas.forEach(function (e) {
      ajustar(e, false);
    });
  }

  window.Despega = window.Despega || {};
  window.Despega.paginar = { preparar: todas, reajustar: reajustar, mostrar: mostrar };

  function iniciar() {
    todas(document);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(reajustar);
    window.addEventListener("load", reajustar);
    // Contenido que trae HTMX (resultados, un paso nuevo): puede traer listas nuevas.
    // Un <details> que se abre o se cierra cambia lo que cabe.
    document.addEventListener("toggle", reajustar, true);
    document.addEventListener("htmx:afterSettle", function () {
      listas = listas.filter(function (e) {
        return document.contains(e.lista);
      });
      todas(document);
      reajustar();
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
