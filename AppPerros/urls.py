from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Si quieres activar el admin de Django:
    # path('admin/', admin.site.urls),

    path('', include('perros.urls')),  # TODA la app cuelga de la raíz
]
