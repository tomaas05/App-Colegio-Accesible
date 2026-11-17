"""HU-03-04, HU-03-05 y HU-03-06: excepciones por fecha, fecha de cancelación y plan B con orden.

El plan B pasa de un ManyToMany sin orden (`Tarea.planes_b`) a la tabla PlanB con su
prioridad (RF3.4.3, RI3.3.1). Los planes B que ya había se copian en el orden en que se
añadieron. Las series ya canceladas quedan canceladas desde el día de esta migración.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q
from django.utils import timezone


def copiar_planes_b(apps, schema_editor):
    Tarea = apps.get_model("tareas", "Tarea")
    PlanB = apps.get_model("tareas", "PlanB")
    Relacion = Tarea.planes_b_antiguo.through
    orden = {}
    nuevos = []
    for fila in Relacion.objects.order_by("pk"):
        if fila.from_tarea_id == fila.to_tarea_id:
            continue
        orden[fila.from_tarea_id] = orden.get(fila.from_tarea_id, 0) + 1
        nuevos.append(
            PlanB(
                tarea_id=fila.from_tarea_id,
                alternativa_id=fila.to_tarea_id,
                orden=orden[fila.from_tarea_id],
            )
        )
    PlanB.objects.bulk_create(nuevos)


def copiar_planes_b_atras(apps, schema_editor):
    Tarea = apps.get_model("tareas", "Tarea")
    PlanB = apps.get_model("tareas", "PlanB")
    Relacion = Tarea.planes_b_antiguo.through
    Relacion.objects.bulk_create(
        Relacion(from_tarea_id=p.tarea_id, to_tarea_id=p.alternativa_id)
        for p in PlanB.objects.order_by("tarea_id", "orden")
    )


def fechar_canceladas(apps, schema_editor):
    Asignacion = apps.get_model("tareas", "Asignacion")
    Asignacion.objects.filter(cancelada=True, cancelada_el__isnull=True).update(
        cancelada_el=timezone.localdate()
    )


class Migration(migrations.Migration):
    dependencies = [
        ("tareas", "0006_asignacion_cancelada"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Plan B con orden ---
        # El nombre antiguo se aparta para que la tabla nueva pueda usar `planes_b`.
        migrations.RenameField("tarea", "planes_b", "planes_b_antiguo"),
        migrations.CreateModel(
            name="PlanB",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("orden", models.PositiveSmallIntegerField()),
                (
                    "alternativa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="es_plan_b_de",
                        to="tareas.tarea",
                        verbose_name="alternativa",
                    ),
                ),
                (
                    "tarea",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="planes_b",
                        to="tareas.tarea",
                    ),
                ),
            ],
            options={
                "verbose_name": "plan B",
                "verbose_name_plural": "planes B",
                "ordering": ["tarea", "orden", "pk"],
                "constraints": [
                    models.UniqueConstraint(fields=("tarea", "alternativa"), name="plan_b_sin_repetir"),
                    models.CheckConstraint(condition=~Q(tarea=F("alternativa")), name="plan_b_no_es_la_misma"),
                    models.CheckConstraint(condition=Q(orden__gt=0), name="plan_b_orden_positivo"),
                ],
            },
        ),
        migrations.RunPython(copiar_planes_b, copiar_planes_b_atras),
        migrations.RemoveField("tarea", "planes_b_antiguo"),
        # --- Cancelar toda la serie: desde qué día ---
        migrations.AddField(
            model_name="asignacion",
            name="cancelada_el",
            field=models.DateField(blank=True, null=True, verbose_name="cancelada desde"),
        ),
        migrations.RunPython(fechar_canceladas, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="asignacion",
            constraint=models.CheckConstraint(
                condition=Q(cancelada=False) | Q(cancelada_el__isnull=False),
                name="asignacion_cancelada_con_fecha",
            ),
        ),
        # --- Cambiar o cancelar un solo día ---
        migrations.CreateModel(
            name="ExcepcionAsignacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateField()),
                ("tipo", models.CharField(choices=[("modificada", "Modificada"), ("cancelada", "Cancelada")], max_length=10)),
                ("hora_inicio", models.TimeField(blank=True, null=True)),
                ("hora_fin", models.TimeField(blank=True, null=True)),
                ("creada_el", models.DateTimeField(auto_now_add=True)),
                (
                    "asignacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="excepciones",
                        to="tareas.asignacion",
                    ),
                ),
                (
                    "creada_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="excepciones_hechas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "excepción de una asignación",
                "verbose_name_plural": "excepciones de asignaciones",
                "ordering": ["asignacion", "fecha"],
                "constraints": [
                    models.UniqueConstraint(fields=("asignacion", "fecha"), name="excepcion_una_por_dia"),
                    models.CheckConstraint(condition=Q(tipo__in=["modificada", "cancelada"]), name="excepcion_tipo_valido"),
                    models.CheckConstraint(
                        condition=(
                            Q(tipo="modificada", hora_inicio__isnull=False, hora_fin__gt=F("hora_inicio"))
                            | Q(tipo="cancelada", hora_inicio__isnull=True, hora_fin__isnull=True)
                        ),
                        name="excepcion_horas_coherentes",
                    ),
                ],
            },
        ),
    ]
