from django.urls import path
from perros.views import listar_perros, mostrar_razas, login_usuario, registrar_usuario, inicio, logout_usuario

urlpatterns = [
    path('perros/', listar_perros),

    path('razas/', mostrar_razas),

    path('login/', login_usuario),

    path('registro/', registrar_usuario),

    path('', inicio, name="inicio"),

    path ('logout/', logout_usuario, name="logout"),
]