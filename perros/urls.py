from django.urls import path
from perros.views import listar_perros, mostrar_razas, login_usuario, registrar_usuario, inicio, logout_usuario, \
    detalle_perro
from . import views

urlpatterns = [
    path('perros/', listar_perros),

    path('razas/', mostrar_razas),

    path('login/', login_usuario),

    path('registro/', registrar_usuario),

    path('', inicio, name="inicio"),

    path('logout/', logout_usuario, name="logout"),

    path('perro/<int:code>/', detalle_perro, name="detalle_perro"),

    path("cargar-fichero/", views.cargar_fichero, name="cargar_fichero"),

    path("subir-fichero/", views.subir_fichero, name="subir_fichero"),

    # CRUD CATEGORIAS
    path('admin/categorias/', views.categorias_list, name='categorias_list'),
    path('admin/categorias/nueva/', views.categoria_create, name='categoria_create'),
    path('admin/categorias/editar/<int:pk>/', views.categoria_update, name='categoria_update'),
    path('admin/categorias/eliminar/<int:pk>/', views.categoria_delete, name='categoria_delete'),

    # GESTION DE VALORES DE CATEGORIA
    path(
        'admin/categorias/<int:category_id>/valores/',
        views.category_values_list,
        name='category_values_list'
    ),
    path(
        'admin/categorias/<int:category_id>/valores/nuevo/',
        views.category_value_create,
        name='category_value_create'
    ),
    path(
        'admin/valores/editar/<int:pk>/',
        views.category_value_update,
        name='category_value_update'
    ),
    path(
        'admin/valores/eliminar/<int:pk>/',
        views.category_value_delete,
        name='category_value_delete'
    ),

]
