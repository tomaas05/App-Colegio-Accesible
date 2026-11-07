"""Carga datos de prueba ficticios para desarrollar sin depender de otras HU.

Uso:
    python manage.py cargar_datos_prueba               # carga si la base está vacía
    python manage.py cargar_datos_prueba --reiniciar   # borra los datos y los vuelve a cargar
    python manage.py cargar_datos_prueba --tarea-ahora # tarea para Lucía dentro de 1 minuto

Todos los datos son inventados. Las imágenes son marcadores de posición
generados al vuelo (cuadros de color con texto), no pictogramas reales.
"""

import io
import shutil
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from apps.agenda.models import Ejecucion, EjecucionPaso, EstadoEjecucion, EstadoPaso
from apps.horario.models import Asignatura, Franja, HorarioClase, TipoAsignatura
from apps.perfil.models import Paleta, TamanoBotones, TamanoLetra, Tema, TipoTemporizador
from apps.tareas.models import Ambito, Asignacion, Paso, Tarea
from apps.usuarios.models import Atencion, Clase, Estudiante, Rol, Usuario

CONTRASENA = "despega2026"
CURSO = "2026-2027"
TODOS_LOS_DIAS = [1, 2, 3, 4, 5, 6, 7]  # también fin de semana, para poder probar cualquier día
CARPETAS_MEDIA = ["avatares", "tareas", "pasos", "asignaturas", "clases"]

# Colores oscuros: el texto blanco encima cumple contraste AA.
COLORES = ["#0B3C49", "#1F6F6B", "#7A3E9D", "#B54708", "#1D4ED8", "#9F1239", "#3F6212", "#5B21B6"]


def imagen(texto, color, nombre, redonda=False):
    """Genera un PNG de 256×256 con un texto centrado (marcador de posición)."""
    lado = 256
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    if redonda:
        dibujo.ellipse((0, 0, lado - 1, lado - 1), fill=color)
    else:
        dibujo.rounded_rectangle((0, 0, lado - 1, lado - 1), radius=40, fill=color)
    tamano = 120 if len(texto) <= 2 else 46
    fuente = ImageFont.load_default(size=tamano)
    caja = dibujo.textbbox((0, 0), texto, font=fuente)
    x = (lado - (caja[2] - caja[0])) / 2 - caja[0]
    y = (lado - (caja[3] - caja[1])) / 2 - caja[1]
    dibujo.text((x, y), texto, font=fuente, fill="white")
    salida = io.BytesIO()
    lienzo.save(salida, format="PNG")
    return ContentFile(salida.getvalue(), name=f"{nombre}.png")


class Command(BaseCommand):
    help = "Carga datos de prueba ficticios (usuarios, clases, horario, tareas y asignaciones)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reiniciar",
            action="store_true",
            help="Borra todos los datos (también los usuarios) y los carga de nuevo.",
        )
        parser.add_argument(
            "--tarea-ahora",
            action="store_true",
            help="Añade a Lucía una tarea que empieza dentro de un minuto y dura 15.",
        )

    def handle(self, *args, **opciones):
        if opciones["reiniciar"]:
            self.borrar_todo()
        elif Usuario.objects.filter(username="tutor").exists():
            self.stdout.write(
                self.style.WARNING(
                    "Los datos de prueba ya están cargados. Usa --reiniciar para recargarlos."
                )
            )
            if opciones["tarea_ahora"]:
                self.tarea_ahora()
            return

        with transaction.atomic():
            self.cargar()
        if opciones["tarea_ahora"]:
            self.tarea_ahora()
        self.resumen()

    # ------------------------------------------------------------------ borrar
    def borrar_todo(self):
        with transaction.atomic():
            Ejecucion.objects.all().delete()
            Asignacion.objects.all().delete()
            Paso.objects.all().delete()
            Tarea.objects.all().delete()
            HorarioClase.objects.all().delete()
            Asignatura.objects.all().delete()
            Franja.objects.all().delete()
            Atencion.objects.all().delete()
            Estudiante.objects.all().delete()
            Clase.objects.all().delete()
            Usuario.objects.all().delete()
        for carpeta in CARPETAS_MEDIA:
            shutil.rmtree(settings.MEDIA_ROOT / carpeta, ignore_errors=True)
        self.stdout.write("Datos anteriores borrados.")

    # ------------------------------------------------------------------ cargar
    def cargar(self):
        hoy = timezone.localdate()

        # --- Adultos -------------------------------------------------------
        Usuario.objects.create_superuser("admin", password=CONTRASENA, first_name="Administración")
        tutora = self.adulto("tutor", "Ana", "Martín Ruiz", Rol.TUTOR)
        tutor2 = self.adulto("tutor2", "Pedro", "Gómez Sanz", Rol.TUTOR)
        profesional = self.adulto("profesional", "Luis", "Navarro Gil", Rol.PROFESIONAL)
        familiar = self.adulto("familiar", "Carmen", "López Vega", Rol.FAMILIAR)
        familiar2 = self.adulto("familiar2", "Javier", "Ortega Ramos", Rol.FAMILIAR)

        # --- Clases --------------------------------------------------------
        clase_a = Clase(nombre="PTVAL 1", curso_escolar=CURSO, descripcion_imagen="Clase PTVAL 1")
        clase_a.imagen.save("ptval1.png", imagen("P1", COLORES[0], "ptval1"), save=False)
        clase_a.save()
        clase_b = Clase(nombre="PTVAL 2", curso_escolar=CURSO, descripcion_imagen="Clase PTVAL 2")
        clase_b.imagen.save("ptval2.png", imagen("P2", COLORES[1], "ptval2"), save=False)
        clase_b.save()

        # --- Estudiantes ---------------------------------------------------
        nombres_a = [
            ("A01", "Lucía", "Fernández"),
            ("A02", "Mateo", "García"),
            ("A03", "Sofía", "Moreno"),
            ("A04", "Hugo", "Romero"),
            ("A05", "Martina", "Alonso"),
            ("A06", "Leo", "Jiménez"),
        ]
        nombres_b = [
            ("B01", "Daniela", "Torres"),
            ("B02", "Pablo", "Díaz"),
            ("B03", "Vega", "Ruiz"),
        ]
        estudiantes_a = [
            self.estudiante(c, n, a, clase_a, tutora, hoy, i)
            for i, (c, n, a) in enumerate(nombres_a)
        ]
        estudiantes_b = [
            self.estudiante(c, n, a, clase_b, tutor2, hoy, i + 3)
            for i, (c, n, a) in enumerate(nombres_b)
        ]
        lucia, mateo, sofia, hugo = estudiantes_a[:4]

        # Familiares: Carmen es la familiar de Lucía; Javier, de Daniela.
        for estudiante, adulto in [(lucia, familiar), (estudiantes_b[0], familiar2)]:
            estudiante.familiar = adulto
            estudiante.fecha_alta_familiar = hoy - timedelta(days=30)
            estudiante.save()

        # Luis (logopeda) atiende a Lucía y a Hugo.
        Atencion.objects.create(profesional=profesional, estudiante=lucia)
        Atencion.objects.create(profesional=profesional, estudiante=hugo)

        # Perfiles variados (el perfil se crea solo al crear el estudiante).
        p = lucia.perfil
        p.tamano_letra, p.tamano_botones = TamanoLetra.GRANDE, TamanoBotones.GRANDE
        p.tipo_temporizador, p.puede_ocultar_temporizador = TipoTemporizador.RADIAL, True
        p.save()
        p = mateo.perfil
        p.tema, p.tipo_temporizador = Tema.OSCURO, TipoTemporizador.NUMERICO
        p.save()
        p = sofia.perfil
        p.paleta, p.max_tarjetas = Paleta.ALTO_CONTRASTE, 3
        p.tamano_botones, p.tamano_letra = TamanoBotones.MUY_GRANDE, TamanoLetra.MUY_GRANDE
        p.save()

        # --- Horario escolar -----------------------------------------------
        horas = [
            ((9, 0), (10, 0)),
            ((10, 0), (11, 0)),
            ((11, 30), (12, 30)),
            ((12, 30), (13, 30)),
            ((13, 30), (14, 30)),
        ]
        franjas = [
            Franja.objects.create(orden=i + 1, hora_inicio=time(*ini), hora_fin=time(*fin))
            for i, (ini, fin) in enumerate(horas)
        ]
        materias = [
            ("Lengua", TipoAsignatura.ASIGNATURA, "Le"),
            ("Matemáticas", TipoAsignatura.ASIGNATURA, "Ma"),
            ("Educación física", TipoAsignatura.ASIGNATURA, "EF"),
            ("Música", TipoAsignatura.ASIGNATURA, "Mú"),
            ("Taller de cocina", TipoAsignatura.TALLER, "Co"),
            ("Taller de reprografía", TipoAsignatura.TALLER, "Re"),
            ("Huerto", TipoAsignatura.TALLER, "Hu"),
        ]
        asignaturas = []
        for i, (nombre, tipo, sigla) in enumerate(materias):
            asignatura = Asignatura(nombre=nombre, tipo=tipo, descripcion_imagen=nombre)
            asignatura.imagen.save(
                f"asig{i}.png", imagen(sigla, COLORES[i % len(COLORES)], f"asig{i}"), save=False
            )
            asignatura.save()
            asignaturas.append(asignatura)
        for desplazamiento, clase in [(0, clase_a), (3, clase_b)]:
            for dia in range(1, 6):
                for f, franja in enumerate(franjas):
                    asignatura = asignaturas[(dia + f + desplazamiento) % len(asignaturas)]
                    HorarioClase.objects.create(
                        clase=clase, dia_semana=dia, franja=franja, asignatura=asignatura
                    )

        # --- Tareas y pasos ------------------------------------------------
        mochila = self.tarea(
            "Preparar la mochila",
            "Meter en la mochila lo que necesito para hoy.",
            "Mo",
            Ambito.ESCOLAR,
            tutora,
            0,
            ["Coger la agenda", "Meter el estuche", "Meter el almuerzo", "Cerrar la mochila"],
        )
        manos = self.tarea(
            "Lavarse las manos",
            "Lavarse las manos con agua y jabón antes de comer.",
            "Ma",
            Ambito.ESCOLAR,
            tutora,
            1,
            ["Abrir el grifo", "Poner jabón", "Aclarar y secar"],
        )
        regar = self.tarea(
            "Regar las plantas",
            "Regar las plantas del huerto con la regadera.",
            "Ri",
            Ambito.ESCOLAR,
            tutora,
            2,
            [],
        )
        cuento = self.tarea(
            "Leer un cuento",
            "Elegir un cuento de la biblioteca y leerlo.",
            "Cu",
            Ambito.OCIO,
            tutora,
            3,
            [],
        )
        mesa = self.tarea(
            "Poner la mesa",
            "Ayudar a poner la mesa para la cena.",
            "Me",
            Ambito.CASA,
            familiar,
            4,
            ["Poner el mantel", "Poner los platos", "Poner los cubiertos"],
        )

        # --- Asignaciones --------------------------------------------------
        desde = hoy - timedelta(days=7)
        plan_a = [
            (mochila, (9, 0), (9, 15)),
            (manos, (10, 30), (10, 45)),
            (regar, (12, 0), (12, 30)),
            (cuento, (17, 0), (17, 30)),
        ]
        for estudiante in estudiantes_a:
            for tarea, ini, fin in plan_a:
                self.asignar(tarea, estudiante, tutora, ini, fin, desde)
        for estudiante in estudiantes_b:
            self.asignar(mochila, estudiante, tutor2, (9, 0), (9, 15), desde)
            self.asignar(manos, estudiante, tutor2, (11, 0), (11, 15), desde)
        # Tarea de casa que pone la familiar de Lucía.
        self.asignar(mesa, lucia, familiar, (20, 0), (20, 20), desde)

        # --- Historial de ayer para Lucía ----------------------------------
        ayer = hoy - timedelta(days=1)
        hecha = Ejecucion.objects.create(
            asignacion=lucia.asignaciones.get(tarea=mochila),
            fecha=ayer,
            inicio_real=self.momento(ayer, 9, 1),
            fin_real=self.momento(ayer, 9, 12),
            estado=EstadoEjecucion.HECHA,
        )
        for paso in mochila.pasos.all():
            EjecucionPaso.objects.create(ejecucion=hecha, paso=paso, estado=EstadoPaso.HECHO)
        Ejecucion.objects.create(
            asignacion=lucia.asignaciones.get(tarea=manos),
            fecha=ayer,
            estado=EstadoEjecucion.VENCIDA,
        )
        Ejecucion.objects.create(
            asignacion=lucia.asignaciones.get(tarea=regar),
            fecha=ayer,
            inicio_real=self.momento(ayer, 12, 5),
            fin_real=self.momento(ayer, 12, 28),
            estado=EstadoEjecucion.HECHA,
        )

    # ------------------------------------------------------------- auxiliares
    def adulto(self, username, nombre, apellidos, rol):
        usuario = Usuario(username=username, first_name=nombre, last_name=apellidos, rol=rol)
        usuario.set_password(CONTRASENA)
        usuario.save()
        return usuario

    def estudiante(self, codigo, nombre, apellidos, clase, tutor, hoy, color):
        usuario = Usuario(
            username=f"est-{codigo.lower()}",
            first_name=nombre,
            last_name=apellidos,
            rol=Rol.ESTUDIANTE,
        )
        usuario.set_unusable_password()
        usuario.save()
        estudiante = Estudiante(
            usuario=usuario,
            codigo_estudiante=codigo,
            clase=clase,
            tutor=tutor,
            fecha_alta_tutor=hoy - timedelta(days=60),
        )
        estudiante.avatar.save(
            f"{codigo.lower()}.png",
            imagen(nombre[0], COLORES[color % len(COLORES)], codigo.lower(), redonda=True),
            save=False,
        )
        estudiante.save()
        return estudiante

    def tarea(self, nombre, descripcion, sigla, ambito, creador, color, pasos):
        tarea = Tarea(
            nombre=nombre,
            descripcion=descripcion,
            descripcion_imagen=nombre,
            ambito=ambito,
            creador=creador,
        )
        tarea.imagen.save(
            f"t{color}.png", imagen(sigla, COLORES[color % len(COLORES)], f"t{color}"), save=False
        )
        tarea.save()
        for orden, texto in enumerate(pasos, start=1):
            paso = Paso(tarea=tarea, orden=orden, descripcion=texto, descripcion_imagen=texto)
            paso.imagen.save(
                f"t{color}p{orden}.png",
                imagen(str(orden), COLORES[(color + 2) % len(COLORES)], f"t{color}p{orden}"),
                save=False,
            )
            paso.save()
        return tarea

    def asignar(self, tarea, estudiante, por, inicio, fin, desde):
        return Asignacion.objects.create(
            tarea=tarea,
            estudiante=estudiante,
            asignado_por=por,
            hora_inicio=time(*inicio),
            hora_fin=time(*fin),
            dias_semana=TODOS_LOS_DIAS,
            vigencia_desde=desde,
        )

    @staticmethod
    def momento(dia, hora, minuto):
        return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))

    def tarea_ahora(self):
        lucia = Estudiante.objects.get(codigo_estudiante="A01")
        ahora = timezone.localtime() + timedelta(minutes=1)
        inicio = ahora.replace(second=0, microsecond=0)
        fin = inicio + timedelta(minutes=15)
        if fin.date() != inicio.date():
            self.stdout.write(self.style.WARNING("Es casi medianoche: no se añade la tarea."))
            return
        solapa = [
            a
            for a in lucia.asignaciones.all()
            if a.aplica_el(inicio.date())
            and a.hora_inicio < fin.time()
            and a.hora_fin > inicio.time()
        ]
        if solapa:
            self.stdout.write(
                self.style.WARNING(f"No se añade: se solaparía con «{solapa[0].tarea}».")
            )
            return
        tarea = Tarea.objects.get(nombre="Lavarse las manos")
        Asignacion.objects.create(
            tarea=tarea,
            estudiante=lucia,
            asignado_por=lucia.tutor,
            hora_inicio=inicio.time(),
            hora_fin=fin.time(),
            dias_semana=[inicio.isoweekday()],
            vigencia_desde=inicio.date(),
            vigencia_hasta=inicio.date(),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Tarea para Lucía hoy de {inicio:%H:%M} a {fin:%H:%M}: «{tarea.nombre}»."
            )
        )

    def resumen(self):
        self.stdout.write(self.style.SUCCESS("Datos de prueba cargados."))
        self.stdout.write(
            f"\n  Contraseña de todos los adultos: {CONTRASENA}\n"
            "  admin        Administración (también entra en /admin/)\n"
            "  tutor        Ana, tutora de PTVAL 1 (6 estudiantes)\n"
            "  tutor2       Pedro, tutor de PTVAL 2 (3 estudiantes)\n"
            "  profesional  Luis, logopeda; atiende a Lucía y a Hugo\n"
            "  familiar     Carmen, familiar de Lucía\n"
            "  familiar2    Javier, familiar de Daniela\n"
            "\n  Estudiantes (entran con su avatar): Lucía, Mateo, Sofía, Hugo, Martina y Leo\n"
            "  en PTVAL 1; Daniela, Pablo y Vega en PTVAL 2.\n"
            f"  {Tarea.objects.count()} tareas, {Asignacion.objects.count()} asignaciones, "
            f"{HorarioClase.objects.count()} casillas de horario, "
            f"{Ejecucion.objects.count()} ejecuciones de ayer (Lucía).\n"
        )
