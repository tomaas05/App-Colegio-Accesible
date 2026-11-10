"""Cargar una lista de estudiantes desde un CSV (HU-01-01, prueba de aceptación 4).

Cada fila se valida con el mismo formulario que «Crear cuenta» y se crea por separado:
una fila mal no impide crear las demás, y se dice cuál es y por qué.

Columnas (la primera fila son los nombres; da igual mayúsculas y tildes):
    nombre; apellidos; imagenes; contrasena
- imagenes: 3 palabras de la rejilla separadas por espacios («perro sol flor»).
- contrasena: su contraseña de texto, si no entra con imágenes.
Una de las dos, no las dos. Separador «;» (el Excel en español) o «,».
"""

import csv
import io
from dataclasses import dataclass, field

from django.db import transaction

from apps.perfil.models import MetodoAcceso

from .forms import CrearCuentaForm
from .models import ImagenAcceso, Rol
from .texto import normalizar

MAXIMO_FILAS = 500
COLUMNAS = ["nombre", "apellidos", "imagenes", "contrasena"]
PLANTILLA = (
    "nombre;apellidos;imagenes;contrasena\r\n"
    "Lucía;García Pérez;perro sol flor;\r\n"
    "Mateo;López Ruiz;;mateo2026\r\n"
)


class PuntoYComa(csv.excel):
    delimiter = ";"


@dataclass
class ResultadoCarga:
    creados: list = field(default_factory=list)  # Estudiante
    errores: list = field(default_factory=list)  # (número de fila, nombre, motivo)
    error_archivo: str = ""


def _leer(archivo):
    datos = archivo.read()
    # Excel en Windows guarda a veces en cp1252. latin-1 lee cualquier byte: con un archivo
    # raro salen letras extrañas en la fila (y se dice cuál falla), nunca un error 500.
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = datos.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialecto = csv.Sniffer().sniff(texto.splitlines()[0] if texto else "", delimiters=";,")
    except csv.Error:
        dialecto = PuntoYComa  # una sola columna o algo raro: el de Excel en español
    return list(csv.reader(io.StringIO(texto), dialecto))


def _motivo(form):
    return " ".join(str(e) for errores in form.errors.values() for e in errores)


def cargar_lista(archivo, clase):
    resultado = ResultadoCarga()
    filas = _leer(archivo)
    if not filas:
        resultado.error_archivo = "El archivo está vacío."
        return resultado

    cabecera = [normalizar(c) for c in filas[0]]
    if "nombre" not in cabecera:
        resultado.error_archivo = (
            "La primera fila tiene que tener los nombres de las columnas: "
            "nombre; apellidos; imagenes; contrasena."
        )
        return resultado
    if len(filas) - 1 > MAXIMO_FILAS:
        resultado.error_archivo = f"Como mucho {MAXIMO_FILAS} estudiantes por archivo."
        return resultado

    posicion = {nombre: cabecera.index(nombre) for nombre in COLUMNAS if nombre in cabecera}
    imagenes_por_palabra = {
        normalizar(i.descripcion_imagen): i.pk for i in ImagenAcceso.objects.filter(activa=True)
    }

    for numero, fila in enumerate(filas[1:], start=2):
        if not any(celda.strip() for celda in fila):
            continue  # filas vacías al final del Excel

        def celda(nombre, fila=fila):
            i = posicion.get(nombre)
            return fila[i].strip() if i is not None and i < len(fila) else ""

        nombre = celda("nombre")
        palabras = celda("imagenes").split()
        contrasena = celda("contrasena")
        if palabras and contrasena:
            resultado.errores.append(
                (numero, nombre, "Pon sus imágenes o su contraseña, no las dos.")
            )
            continue
        if not palabras and not contrasena:
            resultado.errores.append((numero, nombre, "Pon sus 3 imágenes o su contraseña."))
            continue
        desconocidas = [p for p in palabras if normalizar(p) not in imagenes_por_palabra]
        if desconocidas:
            resultado.errores.append(
                (numero, nombre, f"No hay ninguna imagen «{desconocidas[0]}» en la rejilla.")
            )
            continue

        form = CrearCuentaForm(
            {
                "rol": Rol.ESTUDIANTE,
                "nombre": nombre,
                "apellidos": celda("apellidos"),
                "clase": clase.pk,
                "metodo_acceso": MetodoAcceso.CONTRASENA if contrasena else MetodoAcceso.IMAGENES,
                "imagenes": [imagenes_por_palabra[normalizar(p)] for p in palabras],
                "contrasena_estudiante": contrasena,
            }
        )
        if not form.is_valid():
            resultado.errores.append((numero, nombre, _motivo(form)))
            continue
        with transaction.atomic():
            resultado.creados.append(form.crear().estudiante)
    return resultado
