from django.urls import path
from perros.views import *
urlpatterns = [
 path('registro/', registrar_usuario, name='registro'),
 path('login/', login_usuario, name='login'),
 path('logout/', logout_usuario, name='logout'),
]
