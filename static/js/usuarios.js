/*
 * Despega · Pantallas de usuarios y acceso.
 * Sin JavaScript todo funciona igual: esto solo añade ayudas.
 */

/* HU-01-07 y HU-01-06 · Botón «Mostrar / Ocultar» de la contraseña. */
document.querySelectorAll("[data-ver-clave]").forEach((boton) => {
  const campo = document.getElementById(boton.getAttribute("aria-controls"));
  if (!campo) return;
  boton.hidden = false;
  boton.addEventListener("click", () => {
    const ver = campo.type === "password";
    campo.type = ver ? "text" : "password";
    boton.textContent = ver ? "Ocultar" : "Mostrar";
    boton.setAttribute("aria-pressed", String(ver));
  });
});

/*
 * HU-01-06 · Rejilla de la contraseña de imágenes: cuenta las elegidas y, con 3,
 * desactiva el resto para que no se pueda marcar una cuarta. Quitando una se
 * puede elegir otra. El servidor comprueba igualmente que sean 3.
 */
const MAXIMO_IMAGENES = 3;
document.querySelectorAll("[data-rejilla-acceso]").forEach((rejilla) => {
  const casillas = [...rejilla.querySelectorAll('input[type="checkbox"]')];
  const contador = document.querySelector("[data-contador]");
  const numero = document.querySelector("[data-contador-n]");
  const actualizar = () => {
    const elegidas = casillas.filter((c) => c.checked).length;
    casillas.forEach((c) => {
      c.disabled = !c.checked && elegidas >= MAXIMO_IMAGENES;
    });
    if (numero) numero.textContent = String(elegidas);
  };
  if (contador) contador.hidden = false;
  casillas.forEach((c) => c.addEventListener("change", actualizar));
  actualizar();
});

/*
 * HU-01-01 · Crear cuenta (B21): solo se ve la sección del rol elegido y, para un
 * estudiante, la rejilla o la contraseña según «Cómo entra». Sin JavaScript se ve
 * todo y el servidor comprueba igualmente qué hace falta para cada rol.
 */
document.querySelectorAll("[data-crear-cuenta]").forEach((form) => {
  const rol = form.querySelector('select[name="rol"]');
  const metodos = [...form.querySelectorAll('input[name="metodo_acceso"]')];
  const actualizar = () => {
    const tipo = !rol.value ? "" : rol.value === "estudiante" ? "estudiante" : "adulto";
    form.querySelectorAll("[data-solo]").forEach((seccion) => {
      seccion.hidden = seccion.dataset.solo !== tipo;
    });
    const metodo = (metodos.find((m) => m.checked) || {}).value || "imagenes";
    form.querySelectorAll("[data-solo-metodo]").forEach((parte) => {
      parte.hidden = parte.dataset.soloMetodo !== metodo;
    });
  };
  rol.addEventListener("change", actualizar);
  metodos.forEach((m) => m.addEventListener("change", actualizar));
  actualizar();
});

/* Si el formulario vuelve con errores, el foco va al resumen para que se lea primero. */
document.querySelector("[data-enfocar]")?.focus();

/*
 * HU-01-04 · Vínculos (B25). Al escribir en «Buscar estudiante» la lista se filtra
 * sin recargar (por nombre, apellidos o código; da igual las tildes). Para ver sus
 * vínculos se pulsa el botón: cambiar la lista no lleva a otra página (WCAG 3.2.2).
 */
const sinTildes = (texto) =>
  texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

document.querySelectorAll("[data-elegir-estudiante]").forEach((form) => {
  const buscar = form.querySelector('input[name="q"]');
  const lista = form.querySelector('select[name="estudiante"]');
  if (!buscar || !lista) return;
  const grupos = [...lista.querySelectorAll("optgroup")].map((g) => g.cloneNode(true));
  if (!grupos.length) return;
  buscar.addEventListener("input", () => {
    const q = sinTildes(buscar.value);
    const elegido = lista.value;
    lista.replaceChildren();
    grupos.forEach((grupo) => {
      const opciones = [...grupo.children].filter(
        (o) => !q || sinTildes(o.textContent).includes(q) || sinTildes(o.value) === q,
      );
      if (!opciones.length) return;
      const copia = grupo.cloneNode(false);
      opciones.forEach((o) => copia.append(o.cloneNode(true)));
      lista.append(copia);
    });
    if (!lista.options.length) {
      lista.append(new Option("Ningún estudiante coincide", ""));
    } else if ([...lista.options].some((o) => o.value === elegido)) {
      lista.value = elegido;
    }
  });
});

/* RF1.2.4 · Al cambiar el tutor se avisa, antes de guardar, de quién deja de verlo. */
document.querySelectorAll("[data-vinculos]").forEach((form) => {
  const tutor = form.querySelector('select[name="tutor"]');
  const aviso = form.querySelector("[data-aviso-tutor]");
  if (!tutor || !aviso) return;
  const { estudiante, tutorActual, tutorActualId } = form.dataset;
  const actualizar = () => {
    const cambia = tutor.value !== tutorActualId;
    aviso.hidden = !cambia;
    if (!cambia) return;
    const nuevo = tutor.value ? tutor.selectedOptions[0].textContent.trim() : "";
    if (tutorActual && nuevo) {
      aviso.textContent = `Al guardar, el tutor pasa de ${tutorActual} a ${nuevo} y ${tutorActual} dejará de ver a ${estudiante} en su panel.`;
    } else if (nuevo) {
      aviso.textContent = `Al guardar, ${nuevo} será el tutor de ${estudiante}.`;
    } else {
      aviso.textContent = `Al guardar, ${estudiante} se queda sin tutor y ${tutorActual} dejará de ver a ${estudiante} en su panel.`;
    }
  };
  tutor.addEventListener("change", actualizar);
  actualizar();
});
