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
