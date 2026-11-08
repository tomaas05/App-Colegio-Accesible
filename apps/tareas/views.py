import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages

from .forms import TareaForm, PasoFormSet
from .models import Tarea

@login_required
def catalogo_tareas(request):
    # Recuperamos todas las tareas guardadas
    tareas = Tarea.objects.all().order_by('-id')
    return render(request, "tareas/catalogo.html", {"tareas": tareas})

@login_required
def crear_tarea(request):
    if request.method == "POST":
        post_data = request.POST.copy()
        file_data = request.FILES.copy()

        # 1. Procesar ARASAAC para la tarea principal
        arasaac_id = post_data.get("arasaac_id_tarea")
        if arasaac_id and not file_data.get("imagen"):
            url = f"https://static.arasaac.org/pictograms/{arasaac_id}/{arasaac_id}_300.png"
            respuesta = requests.get(url)
            if respuesta.status_code == 200:
                file_data["imagen"] = SimpleUploadedFile(
                    name=f"pictograma_tarea_{arasaac_id}.png",
                    content=respuesta.content,
                    content_type="image/png"
                )

        # 2. Instanciar formularios con prefijo 'pasos'
        form = TareaForm(post_data, file_data)
        formset = PasoFormSet(post_data, file_data, prefix="pasos")

        if form.is_valid() and formset.is_valid():
            tarea = form.save(commit=False)
            tarea.creador = request.user
            tarea.save()

            # Procesar y guardar cada paso del formset (incluyendo pictogramas de ARASAAC si los hay)
            for i, paso_form in enumerate(formset.forms):
                if paso_form.cleaned_data and not paso_form.cleaned_data.get('DELETE'):
                    paso = paso_form.save(commit=False)
                    paso.tarea = tarea

                    # Comprobamos si este paso concreto tiene un ID de ARASAAC seleccionado
                    arasaac_paso_id = post_data.get(f"pasos-{i}-arasaac_id_paso")
                    if arasaac_paso_id and not paso.imagen:
                        url_paso = f"https://static.arasaac.org/pictograms/{arasaac_paso_id}/{arasaac_paso_id}_300.png"
                        resp_paso = requests.get(url_paso)
                        if resp_paso.status_code == 200:
                            paso.imagen = SimpleUploadedFile(
                                name=f"pictograma_paso_{arasaac_paso_id}.png",
                                content=resp_paso.content,
                                content_type="image/png"
                            )
                    paso.save()

            # Guardar eliminaciones usando deleted_forms en lugar de deleted_objects
            for form_eliminado in formset.deleted_forms:
                if form_eliminado.instance.pk:
                    form_eliminado.instance.delete()

            messages.success(request, f"La tarea '{tarea.nombre}' se ha creado correctamente.")
            return redirect("tareas:catalogo")
        else:
            # Depuración de errores en consola si la validación falla
            print("--- ERRORES FORMULARIO TAREA ---")
            print(form.errors)
            print("--- ERRORES FORMSET PASOS ---")
            print(formset.errors)
    else:
        form = TareaForm()
        formset = PasoFormSet(prefix="pasos")

    return render(request, "tareas/crear_tarea.html", {
        "form": form,
        "formset": formset,
    })

@login_required
def anadir_paso(request):
    numero_pasos = int(request.GET.get('total_forms', 0))
    formset = PasoFormSet(prefix="pasos")
    form = formset.empty_form

    html_campos = ""
    for hidden in form.hidden_fields():
        html_campos += str(hidden)

    for field in form.visible_fields():
        if field.name in ['DELETE', 'orden']:
            html_campos += f'<div style="display:none;">{field}</div>'
        else:
            # Imprimimos los errores en pantalla con un span rojo si existen
            errores_html = f'<div style="color: var(--error, #991b1b); font-size: 0.85rem; margin-top: 0.25rem;">{field.errors}</div>' if field.errors else ""
            html_campos += f'<p>{field.label_tag()} {field} {errores_html}</p>'

    html_campos = html_campos.replace("__prefix__", str(numero_pasos))

    html = f"""
    <div class="paso-item" id="paso-item-{numero_pasos}" style="background: var(--blanco); padding: 1.5rem; border-radius: 0.75rem; border: 1px solid var(--gris); margin-bottom: 1rem;">
        <h2 class="titulo-paso" style="color: var(--petroleo); margin-top: 0;">Paso {numero_pasos + 1}</h2>
        {html_campos}

        <!-- Buscador ARASAAC específico para el paso -->
        <div class="buscador-arasaac-box" style="margin-top: 1rem; padding: 1rem; background-color: var(--aviso-fondo, #f8fafc); border-radius: 0.75rem; border: 1px solid var(--gris);">
            <label for="buscador-arasaac-{numero_pasos}" style="font-size: 0.9rem; font-weight: bold;">Buscar pictograma en ARASAAC para este paso:</label>
            <div class="buscador-arasaac-flex" style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                <input type="text" id="buscador-arasaac-{numero_pasos}" placeholder="Ej: recortar, pegar..." style="flex: 1; padding: 0.5rem; border: 1px solid var(--gris); border-radius: 0.5rem;">
                <button type="button" onclick="buscarArasaacPaso({numero_pasos})" class="principal" style="padding: 0.5rem 1rem; font-size: 0.9rem;">Buscar</button>
            </div>
            <div id="resultados-arasaac-{numero_pasos}" class="resultados-arasaac-grid" style="display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap;"></div>
            <input type="hidden" name="pasos-{numero_pasos}-arasaac_id_paso" id="id_pasos-{numero_pasos}-{numero_pasos}-arasaac_id_paso" value="">
            <p id="mensaje-pic-paso-{numero_pasos}" style="color: var(--verde-oscuro); font-weight: bold; display: none; margin-top: 0.5rem; font-size: 0.9rem;">✓ Pictograma seleccionado para el paso.</p>
        </div>

        <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
            <button type="button" onclick="moverPaso(this, -1)" class="aux" aria-label="Subir paso">↑</button>
            <button type="button" onclick="moverPaso(this, 1)" class="aux" aria-label="Bajar paso">↓</button>
            <button type="button" onclick="eliminarPaso('{numero_pasos}')" class="aux" style="background-color: var(--error); color: var(--blanco); border-color: var(--error);">Eliminar paso</button>
        </div>
    </div>
    <script>
        document.getElementById('id_pasos-TOTAL_FORMS').value = {numero_pasos + 1};
    </script>
    """
    return HttpResponse(html)
