/*
 * Despega · Pantallas de usuarios y acceso (HU-01-07).
 * Botón «Mostrar / Ocultar» de la contraseña (boceto B12). Sin JavaScript, la
 * contraseña se escribe igual: el botón solo aparece si este archivo se carga.
 */
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
