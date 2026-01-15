from django.urls import path
from perros.views import listar_perros



urlpatterns = [
    path('perros/', listar_perros),
]