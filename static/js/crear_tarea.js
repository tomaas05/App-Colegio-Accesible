// --- 1. LÓGICA DE LOS PASOS ---
function actualizarNumeracion() {
  const pasosVisibles = document.querySelectorAll('.paso-item:not([style*="display: none"])');
  pasosVisibles.forEach((paso, index) => {
    const titulo = paso.querySelector('.titulo-paso');
    if (titulo) titulo.innerText = 'Paso ' + (index + 1);

    const inputOrden = paso.querySelector('input[name$="-orden"]');
    if (inputOrden) inputOrden.value = index + 1;
  });
}

function moverPaso(boton, direccion) {
  const pasoActual = boton.closest('.paso-item');

  if (direccion === -1 && pasoActual.previousElementSibling) {
    pasoActual.parentNode.insertBefore(pasoActual, pasoActual.previousElementSibling);
  } else if (direccion === 1 && pasoActual.nextElementSibling) {
    pasoActual.parentNode.insertBefore(pasoActual.nextElementSibling, pasoActual);
  }

  actualizarNumeracion();
}

function eliminarPaso(indice) {
  const checkboxEliminar = document.getElementById('id_pasos-' + indice + '-DELETE');
  if (checkboxEliminar) checkboxEliminar.checked = true;

  const divPaso = document.getElementById('paso-item-' + indice);
  if (divPaso) divPaso.style.display = 'none';

  actualizarNumeracion();
}

document.body.addEventListener('htmx:afterSwap', function(evt) {
  actualizarNumeracion();
});

// --- 2. LÓGICA DE ARASAAC (TAREA PRINCIPAL) ---
async function buscarArasaac() {
  const palabra = document.getElementById('buscador-arasaac').value.trim();
  const contenedor = document.getElementById('resultados-arasaac');
  contenedor.innerHTML = 'Buscando...';

  if (!palabra) {
    contenedor.innerHTML = 'Escribe una palabra para buscar.';
    return;
  }

  try {
    const respuesta = await fetch(`https://api.arasaac.org/api/pictograms/es/search/${encodeURIComponent(palabra)}`);
    if (!respuesta.ok) throw new Error('No se encontraron resultados');

    const pictogramas = await respuesta.json();
    contenedor.innerHTML = '';

    pictogramas.slice(0, 5).forEach(pic => {
      const urlImagen = `https://static.arasaac.org/pictograms/${pic._id}/${pic._id}_300.png`;

      const img = document.createElement('img');
      img.src = urlImagen;
      img.alt = "Pictograma de ARASAAC";
      img.style.width = '100px';
      img.style.cursor = 'pointer';
      img.style.border = '2px solid transparent';

      img.onclick = () => {
        document.getElementById('arasaac_id_tarea').value = pic._id;
        document.getElementById('mensaje-pictograma-seleccionado').style.display = 'block';

        const inputImagen = document.getElementById('id_imagen');
        if (inputImagen) {
          inputImagen.value = '';
          inputImagen.removeAttribute('required');
        }
      };

      contenedor.appendChild(img);
    });
  } catch (error) {
    contenedor.innerHTML = 'No se encontraron pictogramas para esa palabra.';
  }
}

document.addEventListener("DOMContentLoaded", function() {
  const inputImagen = document.getElementById('id_imagen');
  if (inputImagen) {
    inputImagen.addEventListener('change', function() {
      if (this.value) {
        document.getElementById('arasaac_id_tarea').value = '';
        document.getElementById('mensaje-pictograma-seleccionado').style.display = 'none';
      }
    });
  }
});

// --- 3. LÓGICA DE ARASAAC (PASOS DINÁMICOS) ---
async function buscarArasaacPaso(indice) {
  const inputBuscador = document.getElementById(`buscador-arasaac-${indice}`);
  const palabra = inputBuscador ? inputBuscador.value.trim() : '';
  const contenedor = document.getElementById(`resultados-arasaac-${indice}`);
  contenedor.innerHTML = 'Buscando...';

  if (!palabra) {
    contenedor.innerHTML = 'Escribe una palabra.';
    return;
  }

  try {
    const respuesta = await fetch(`https://api.arasaac.org/api/pictograms/es/search/${encodeURIComponent(palabra)}`);
    if (!respuesta.ok) throw new Error('No se encontraron resultados');

    const pictogramas = await respuesta.json();
    contenedor.innerHTML = '';

    pictogramas.slice(0, 4).forEach(pic => {
      const urlImagen = `https://static.arasaac.org/pictograms/${pic._id}/${pic._id}_300.png`;

      const img = document.createElement('img');
      img.src = urlImagen;
      img.alt = "Pictograma";
      img.style.width = '70px';
      img.style.height = '70px';
      img.style.objectFit = 'contain';
      img.style.cursor = 'pointer';
      img.style.border = '2px solid var(--gris)';
      img.style.borderRadius = '0.5rem';
      img.style.backgroundColor = 'var(--blanco)';

      img.onclick = () => {
        document.getElementById(`id_pasos-${indice}-arasaac_id_paso`).value = pic._id;
        document.getElementById(`mensaje-pic-paso-${indice}`).style.display = 'block';

        const inputFilePaso = document.getElementById(`id_pasos-${indice}-imagen`);
        if (inputFilePaso) inputFilePaso.value = '';
      };

      contenedor.appendChild(img);
    });
  } catch (error) {
    contenedor.innerHTML = 'Sin resultados.';
  }
}

// --- 4. LÓGICA DE CONFIRMACIÓN Y VISTA PREVIA (VALIDACIÓN ESTRICTA) ---
function prepararYMostrarVistaPrevia() {
  const modal = document.getElementById('modal-vista-previa');
  const contenedor = document.getElementById('contenido-vista-previa');

  const nombreInput = document.querySelector('[name="nombre"]');
  const descripcionInput = document.querySelector('textarea[name="descripcion"]');
  const descImgInput = document.querySelector('[name="descripcion_imagen"]');

  const nombre = nombreInput ? nombreInput.value.trim() : '';
  const descripcion = descripcionInput ? descripcionInput.value.trim() : '';
  const descripcionImagen = descImgInput ? descImgInput.value.trim() : '';

  // 1. Validar campos principales obligatorios
  if (!nombre) {
    alert("⚠️ El nombre de la tarea es obligatorio.");
    if (nombreInput) nombreInput.focus();
    return;
  }

  // Comprobar imagen principal (Archivo local o ARASAAC)
  const arasaacId = document.getElementById('arasaac_id_tarea').value;
  const fileInput = document.getElementById('id_imagen');
  const tieneImagenPrincipal = arasaacId || (fileInput && fileInput.files && fileInput.files[0]);

  if (!tieneImagenPrincipal) {
    alert("⚠️ Es obligatorio añadir una imagen principal (subir archivo o buscar pictograma en ARASAAC).");
    return;
  }

  if (!descripcionImagen) {
    alert("⚠️ La descripción de la imagen principal es obligatoria.");
    if (descImgInput) descImgInput.focus();
    return;
  }

  // 2. Validar que obligatoriamente haya al menos un paso y cumpla con todo
  const pasosVisibles = document.querySelectorAll('.paso-item:not([style*="display: none"])');
  if (pasosVisibles.length === 0) {
    alert("⚠️ Debes añadir al menos un paso a la tarea.");
    return;
  }

  for (let i = 0; i < pasosVisibles.length; i++) {
    const paso = pasosVisibles[i];
    const campoTexto = paso.querySelector('textarea, input[type="text"]:not([name$="-orden"]):not([name$="-DELETE"]):not([name$="-arasaac_id_paso"]):not([id*="buscador"])');
    const textoPaso = campoTexto ? campoTexto.value.trim() : '';

    const arasaacPasoInput = paso.querySelector('input[id*="arasaac_id_paso"]');
    const arasaacPasoId = arasaacPasoInput ? arasaacPasoInput.value : '';
    const filePasoInput = paso.querySelector('input[type="file"]');
    const tieneImagenPaso = arasaacPasoId || (filePasoInput && filePasoInput.files && filePasoInput.files[0]);

    const descImgPasoInput = paso.querySelector('input[name$="-descripcion_imagen"]');
    const descImgPaso = descImgPasoInput ? descImgPasoInput.value.trim() : '';

    if (!textoPaso) {
      alert(`⚠️ El Paso ${i + 1} debe contener una descripción.`);
      if (campoTexto) campoTexto.focus();
      return;
    }

    if (!tieneImagenPaso) {
      alert(`⚠️ El Paso ${i + 1} es obligatorio: debes subir una imagen o seleccionar un pictograma de ARASAAC.`);
      return;
    }

    if (!descImgPaso) {
      alert(`⚠️ El Paso ${i + 1} requiere obligatoriamente una descripción de su imagen.`);
      if (descImgPasoInput) descImgPasoInput.focus();
      return;
    }
  }

  // Montar el resumen visual para el tutor
  let imgHtml = '';
  if (arasaacId) {
    imgHtml = `<div style="text-align: center; margin-bottom: 1rem;"><img src="https://static.arasaac.org/pictograms/${arasaacId}/${arasaacId}_300.png" style="max-width: 150px; border-radius: 8px;"></div>`;
  } else if (fileInput && fileInput.files && fileInput.files[0]) {
    const urlTemporal = URL.createObjectURL(fileInput.files[0]);
    imgHtml = `<div style="text-align: center; margin-bottom: 1rem;"><img src="${urlTemporal}" style="max-width: 150px; border-radius: 8px;"></div>`;
  }

  let html = `<h3 style="color: var(--petroleo); margin-top: 0;">${nombre}</h3>`;
  html += imgHtml;
  if (descripcion) {
    html += `<p class="txt"><strong>Descripción:</strong> ${descripcion}</p>`;
  }

  html += `<hr style="margin: 1rem 0; border: 0; border-top: 1px solid var(--gris);">`;
  html += `<h4>Pasos configurados (${pasosVisibles.length}):</h4>`;
  html += `<ul style="padding-left: 1.2rem; max-height: 200px; overflow-y: auto; list-style-type: none;">`;

  pasosVisibles.forEach((paso, index) => {
    const campoTexto = paso.querySelector('textarea, input[type="text"]:not([name$="-orden"]):not([name$="-DELETE"]):not([name$="-arasaac_id_paso"]):not([id*="buscador"])');
    const textoPaso = campoTexto ? campoTexto.value : '';

    const arasaacPasoInput = paso.querySelector('input[id*="arasaac_id_paso"]');
    const arasaacPasoId = arasaacPasoInput ? arasaacPasoInput.value : '';

    let imgPasoHtml = '';
    if (arasaacPasoId) {
      imgPasoHtml = `<img src="https://static.arasaac.org/pictograms/${arasaacPasoId}/${arasaacPasoId}_300.png" style="width: 40px; height: 40px; object-fit: contain; background: var(--blanco); border-radius: 4px; border: 1px solid var(--gris);">`;
    }

    html += `<li style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; padding: 0.5rem; background: var(--aviso-fondo); border-radius: 0.5rem;">
              ${imgPasoHtml}
              <div><strong>Paso ${index + 1}:</strong> ${textoPaso}</div>
             </li>`;
  });
  html += `</ul>`;

  contenedor.innerHTML = html;
  modal.showModal();
}

function cerrarVistaPrevia() {
  document.getElementById('modal-vista-previa').close();
}

function confirmarGuardado() {
  const form = document.querySelector('form');
  if (form) {
    form.submit();
  }
}
