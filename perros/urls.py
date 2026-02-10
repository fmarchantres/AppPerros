from django.urls import path
from perros.views import listar_perros, login_usuario, registrar_usuario, inicio, logout_usuario, detalle_perro
from . import views

urlpatterns = [
    path('perros/', listar_perros),

    path('login/', login_usuario),
    path('registro/', registrar_usuario),

    path('', inicio, name="inicio"),

    path('logout/', logout_usuario, name="logout"),

    path('perro/<int:code>/', detalle_perro, name="detalle_perro"),

    path("cargar-fichero/", views.cargar_fichero, name="cargar_fichero"),
    path("subir-fichero/", views.subir_fichero, name="subir_fichero"),
    path("perro/<int:code>/valorar/", views.rate_dog, name="rate_dog"),


    # =========================
    # CATEGORÍAS
    # =========================
    path('admin/categorias/', views.categorias_list, name='categorias_list'),
    path('admin/categorias/crear/', views.categoria_create, name='categoria_create'),
    path('admin/categorias/<str:category_id>/editar/', views.categoria_update, name='categoria_update'),
    path('admin/categorias/<str:category_id>/eliminar/', views.categoria_delete, name='categoria_delete'),

    # =========================
    # VALORES DE CATEGORÍA
    # =========================
    path(
        'admin/categorias/<str:category_id>/values/',
        views.category_values_list,
        name='category_values_list'
    ),
    path(
        'admin/categorias/<str:category_id>/values/crear/',
        views.category_value_create,
        name='category_value_create'
    ),
    path(
        'admin/values/<str:value_id>/editar/',
        views.category_value_update,
        name='category_value_update'
    ),
    path(
        'admin/values/<str:value_id>/eliminar/',
        views.category_value_delete,
        name='category_value_delete'
    ),
]
