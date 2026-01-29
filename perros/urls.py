from django.urls import path
from perros.views import listar_perros, mostrar_razas, login_usuario, registrar_usuario, inicio, logout_usuario, detalle_perro
from . import views

urlpatterns = [
    path('perros/', listar_perros),

    path('razas/', mostrar_razas),

    path('login/', login_usuario),

    path('registro/', registrar_usuario),

    path('', inicio, name="inicio"),

    path ('logout/', logout_usuario, name="logout"),

    path ('perro/<int:code>/', detalle_perro, name="detalle_perro"),

    path("cargar-fichero/", views.cargar_fichero, name="cargar_fichero"),

    path ("subir-fichero/", views.subir_fichero, name="subir_fichero"),
]