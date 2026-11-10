/*
 * Despega · Vista previa en vivo del perfil visual (HU-04-01).
 */
(() => {
  const form = document.getElementById("perfil-form");
  const previa = document.getElementById("perfil-previa");
  const resumen = document.getElementById("perfil-previa-resumen");
  if (!form || !previa) return;

  const leer = (nombre) => {
    const el = form.querySelector(`input[name="${nombre}"]:checked`);
    return el ? el.value : "";
  };

  const leerEtiqueta = (nombre) => {
    const el = form.querySelector(`input[name="${nombre}"]:checked`);
    const label = el && el.closest("label");
    return label ? label.textContent.trim() : "";
  };

  const actualizar = () => {
    const tema = leer("tema");
    const paleta = leer("paleta");
    const fuente = leer("tipo_letra");
    const letra = leer("tamano_letra");
    const botones = leer("tamano_botones");

    if (tema) previa.dataset.tema = tema;
    if (paleta) previa.dataset.paleta = paleta;
    if (fuente) previa.dataset.fuente = fuente;
    if (letra) previa.dataset.letra = letra;
    if (botones) previa.dataset.botones = botones;

    if (resumen) {
      resumen.textContent =
        `Tema ${leerEtiqueta("tema").toLowerCase()} · ` +
        `Paleta ${leerEtiqueta("paleta").toLowerCase()} · ` +
        `${leerEtiqueta("tipo_letra")} ${letra} px · ` +
        `Botones ${botones} px`;
    }
  };

  form.addEventListener("change", actualizar);
})();
