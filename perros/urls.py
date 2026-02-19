from django.urls import path
from perros.views import listar_perros, login_usuario, registrar_usuario, inicio, logout_usuario, detalle_perro
from . import views


urlpatterns = [

    # =====================================================
    # PÚBLICO / NAVEGACIÓN PRINCIPAL
    # =====================================================

    path('', inicio, name="inicio"),
    path('perros/', listar_perros),
    path('perro/<int:code>/', detalle_perro, name="detalle_perro"),


    # =====================================================
    # AUTENTICACIÓN
    # =====================================================

    path('login/', login_usuario, name="login"),
    path('registro/', registrar_usuario, name="registro"),
    path('logout/', logout_usuario, name="logout"),


    # =====================================================
    # CARGA DE DATOS (CSV / IMPORTACIONES)
    # =====================================================

    path("cargar-fichero/", views.cargar_fichero, name="cargar_fichero"),
    path("subir-fichero/", views.subir_fichero, name="subir_fichero"),


    # =====================================================
    # VALORACIONES
    # =====================================================

    path("perro/<int:code>/valorar/", views.rate_dog, name="rate_dog"),
    path("perro/<int:dog_code>/valorar/", views.rate_dog, name="rate_dog"),
    path("perro/<int:code>/eliminar-valoracion/",
         views.delete_rating,
         name="delete_rating"),


    # =====================================================
    # RANKINGS (USUARIO)
    # =====================================================

    path("rankings/", views.my_rankings, name="my_rankings"),
    path("rankings/crear/", views.create_ranking, name="create_ranking"),
    path("rankings/<str:ranking_id>/", views.ranking_detail, name="ranking_detail"),
    path("ranking/<str:ranking_id>/editar/", views.editar_ranking, name="editar_ranking"),
    path("ranking/<str:ranking_id>/delete/", views.delete_ranking, name="delete_ranking"),
    path("ranking/<int:code>/remove/", views.remove_from_ranking, name="remove_from_ranking"),
    path("ranking/<str:ranking_id>/update-order/",
         views.update_ranking_order,
         name="update_ranking_order"),
    path("perro/<int:code>/add-to-ranking/", views.add_to_ranking, name="add_to_ranking"),


    # =====================================================
    # RANKINGS GLOBALES / POR CATEGORÍA
    # =====================================================

    path("ranking/global/", views.ranking_global, name="ranking_global"),

    path(
        "ranking/grupo/<str:group_name>/",
        views.ranking_por_grupo,
        name="ranking_por_grupo"
    ),

    path("ranking/grupo/<str:group_name>/",
         views.ranking_categoria,
         name="ranking_categoria"),


    # =====================================================
    # ESTADÍSTICAS
    # =====================================================

    path("estadisticas/", views.estadisticas_globales, name="estadisticas"),


    # =====================================================
    # PANEL ADMIN PERSONALIZADO
    # =====================================================

    path("panel-admin/", views.panel_admin, name="panel_admin"),


    # =====================================================
    # ADMIN – ELEMENTOS
    # =====================================================

    path("admin/elementos/", views.admin_elementos_list, name="admin_elementos_list"),
    path("admin/elementos/crear/", views.admin_elemento_create, name="admin_elemento_create"),
    path("admin/elementos/<int:code>/editar/", views.admin_elemento_update, name="admin_elemento_update"),
    path("admin/elementos/<int:code>/eliminar/", views.admin_elemento_delete, name="admin_elemento_delete"),


    # =====================================================
    # ADMIN – CATEGORÍAS
    # =====================================================

    path('admin/categorias/', views.categorias_list, name='categorias_list'),
    path('admin/categorias/crear/', views.categoria_create, name='categoria_create'),
    path('admin/categorias/<str:category_id>/editar/', views.categoria_update, name='categoria_update'),
    path('admin/categorias/<str:category_id>/eliminar/', views.categoria_delete, name='categoria_delete'),


    # =====================================================
    # ADMIN – VALORES DE CATEGORÍA
    # =====================================================

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
