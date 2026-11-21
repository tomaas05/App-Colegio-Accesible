from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.dia, name="dia"),
    path("aviso/", views.aviso, name="aviso"),
    path("semana/", views.semana, name="semana"),
    path("dia/<str:fecha>/", views.otro_dia, name="otro_dia"),
    path("cambio/<int:pk>/visto/", views.aviso_visto, name="aviso_visto"),
    path("tarea/<int:pk>/", views.detalle, name="detalle"),
    path("tarea/<int:pk>/empezar/", views.empezar, name="empezar"),
    path("tarea/<int:pk>/terminar/", views.terminar, name="terminar"),
    path("tarea/<int:pk>/bravo/", views.bravo, name="bravo"),
    path("tarea/<int:pk>/no-puedo/", views.no_puedo, name="no_puedo"),
    path("tarea/<int:pk>/plan-b/", views.plan_b, name="plan_b"),
    path("tarea/<int:pk>/paso/<int:paso_pk>/hecho/", views.paso_hecho, name="paso_hecho"),
]
