from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from datetime import datetime
from pymongo import MongoClient
import csv
import json
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from bson import ObjectId
from django.shortcuts import redirect
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User

from perros.forms import RegistroForm, LoginForm
from perros.models import *

# =========================================================
# MONGODB – CONEXIÓN Y COLECCIONES
# =========================================================

client = MongoClient("mongodb://localhost:27017/")
db = client["dogs"]

dogs_col = db["dogs"]
categories_col = db["categories"]
values_col = db["category_values"]
category_values_col = db["category_values"]
ratings_col = db["ratings"]
rankings_col = db["rankings"]


# =========================================================
# HELPERS / FUNCIONES AUXILIARES
# =========================================================

def is_admin(user):
    return user.is_authenticated and user.role == "admin"


def get_user_rating(user, dog_code):
    if not user.is_authenticated:
        return None

    return ratings_col.find_one({
        "user_id": user.id,
        "dog_code": dog_code
    })


# =========================================================
# API SIMPLE (JSON)
# =========================================================

def listar_perros(request):
    perros = list(dogs_col.find({}, {"_id": 0}))
    return JsonResponse(perros, safe=False)


# =========================================================
# HOME + FILTROS (SOLO MONGO)
# =========================================================

def inicio(request):

    print("AUTH:", request.user.is_authenticated)
    print("USER:", request.user)

    query = {}

    search = request.GET.get("search")
    origin = request.GET.get("origin")
    group = request.GET.get("group")
    life_span = request.GET.get("life")
    temperaments = request.GET.getlist("temperament")
    selected_temperaments = temperaments  #NECESARIO


    # -----------------------------------------------------
    # BUSCADOR POR NOMBRE
    # -----------------------------------------------------
    if search:
        query["name"] = {
            "$regex": search,
            "$options": "i"
        }


    # -----------------------------------------------------
    # FILTROS
    # -----------------------------------------------------
    if origin:
        query["origin"] = origin

    if group:
        query["breed_group"] = group

    if life_span:
        query["life_span"] = {
            "$regex": f"^{life_span}"
        }

    if temperaments:
        query["temperament"] = {
            "$regex": "|".join(temperaments),
            "$options": "i"
        }


    # -----------------------------------------------------
    # CONSULTA A MONGO
    # -----------------------------------------------------
    perros = list(dogs_col.find(query, {"_id": 0}))


    # -----------------------------------------------------
    # PAGINACIÓN
    # -----------------------------------------------------
    paginator = Paginator(perros, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)


    # -----------------------------------------------------
    # OBTENER VALORES ÚNICOS PARA FILTROS
    # -----------------------------------------------------
    origenes = sorted(dogs_col.distinct("origin"))
    grupos = sorted(dogs_col.distinct("breed_group"))
    vidas = sorted(dogs_col.distinct("life_span"))

    temperamentos = sorted(
        set(
            t.strip()
            for dog in dogs_col.find({}, {"temperament": 1})
            if dog.get("temperament")
            for t in dog["temperament"].split(",")
        )
    )

    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------
    return render(request, "inicio.html", {
        "page_obj": page_obj,
        "origenes": origenes,
        "grupos": grupos,
        "vidas": vidas,
        "temperamentos": temperamentos,
        "selected_temperaments": selected_temperaments,
    })


# =========================================================
# DETALLE DE PERRO (SOLO MONGO)
# =========================================================

def detalle_perro(request, code):

    # -----------------------------------------------------
    # BUSCAR PERRO
    # -----------------------------------------------------
    perro = dogs_col.find_one({"code": code}, {"_id": 0})

    if not perro:
        return render(request, "404.html", status=404)


    # -----------------------------------------------------
    # PREPARAR TEMPERAMENTOS
    # -----------------------------------------------------
    temperamento_lista = []
    if perro.get("temperament"):
        temperamento_lista = [
            t.strip() for t in perro["temperament"].split(",")
        ]


    # -----------------------------------------------------
    # ESTADÍSTICAS DE VALORACIONES (AGGREGATION)
    # -----------------------------------------------------
    pipeline = [
        {"$match": {"dog_code": code}},
        {
            "$group": {
                "_id": "$dog_code",
                "avg_score": {"$avg": "$score"},
                "total": {"$sum": 1}
            }
        }
    ]

    stats = list(ratings_col.aggregate(pipeline))

    avg_rating = round(stats[0]["avg_score"], 1) if stats else None
    total_ratings = stats[0]["total"] if stats else 0


    # -----------------------------------------------------
    # VALORACIÓN DEL USUARIO ACTUAL
    # -----------------------------------------------------
    user_rating = None
    if request.user.is_authenticated:
        user_rating = ratings_col.find_one({
            "user_id": request.user.id,
            "dog_code": code
        })


    # -----------------------------------------------------
    # LISTADO DE COMENTARIOS
    # -----------------------------------------------------
    ratings = list(
        ratings_col.find(
            {"dog_code": code},
            {"_id": 0}
        ).sort("created_at", -1)
    )

    # Obtener nombres de usuarios
    user_ids = [r["user_id"] for r in ratings]
    users = User.objects.filter(id__in=user_ids)
    user_map = {u.id: u.username for u in users}

    for r in ratings:
        r["username"] = user_map.get(r["user_id"], "Usuario")


    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------
    return render(request, "detalle_perro.html", {
        "perro": perro,
        "avg_rating": avg_rating,
        "total_ratings": total_ratings,
        "user_rating": user_rating,
        "ratings": ratings,
        "temperamento_lista": temperamento_lista,
    })



    # ==============================
    # ELIMINAR VALORACIÓN
    # ==============================
    @login_required
    def delete_rating(request, code):

        ratings_col.delete_one({
            "user_id": request.user.id,
            "dog_code": code
        })

        messages.success(request, "Valoración eliminada correctamente.")
        return redirect("detalle_perro", code=code)

    # ==============================
    # RANKINGS DEL USUARIO
    # ==============================
    user_rankings = []

    if request.user.is_authenticated:
        for r in rankings_col.find({"user_id": request.user.id}):
            user_rankings.append({
                "id": str(r["_id"]),
                "name": r["name"]
            })

    return render(request, "detalle_perro.html", {
        "perro": perro,
        "user_rating": user_rating,
        "avg_rating": avg_rating,
        "total_ratings": total_ratings,
        "ratings": ratings,
        "user_rankings": user_rankings,
    })


# =========================================================
# VALORACIÓN DE PERROS
# =========================================================

@login_required
def rate_dog(request, code):

    # -----------------------------------------------------
    # VALIDAR METODO
    # -----------------------------------------------------
    if request.method != "POST":
        return redirect("detalle_perro", code=code)

    # -----------------------------------------------------
    # VALIDAR SCORE
    # -----------------------------------------------------
    try:
        score = int(request.POST.get("score"))
    except (TypeError, ValueError):
        return redirect("detalle_perro", code=code)

    comment = request.POST.get("comment", "").strip()

    if score < 1 or score > 5:
        return redirect("detalle_perro", code=code)

    # -----------------------------------------------------
    # COMPROBAR SI YA EXISTE VALORACIÓN
    # -----------------------------------------------------
    existing = ratings_col.find_one({
        "user_id": request.user.id,
        "dog_code": code
    })

    now = datetime.utcnow()

    # -----------------------------------------------------
    # UPDATE O INSERT
    # -----------------------------------------------------
    if existing:
        ratings_col.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "score": score,
                    "comment": comment,
                    "updated_at": now
                }
            }
        )
    else:
        ratings_col.insert_one({
            "user_id": request.user.id,
            "dog_code": code,
            "score": score,
            "comment": comment,
            "created_at": now,
            "updated_at": now
        })

    return redirect("detalle_perro", code=code)


# =========================================================
# ELIMINAR VALORACIÓN
# =========================================================

@login_required
@require_POST
def delete_rating(request, code):

    ratings_col.delete_one({
        "user_id": request.user.id,
        "dog_code": code
    })

    return redirect("detalle_perro", code=code)


# =========================================================
# USUARIOS – REGISTRO / LOGIN / LOGOUT
# =========================================================

def registrar_usuario(request):

    # -----------------------------------------------------
    # REGISTRO
    # -----------------------------------------------------
    if request.method == "POST":
        form = RegistroForm(request.POST)

        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.set_password(form.cleaned_data["password"])
            usuario.save()
            return redirect("login")
    else:
        form = RegistroForm()

    return render(request, "usuarios/registro.html", {"form": form})


def login_usuario(request):

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            return redirect("inicio")
    else:
        form = LoginForm()

    return render(request, "usuarios/login.html", {"form": form})


def logout_usuario(request):

    logout(request)
    return redirect("login")


# =========================================================
# CARGA DE FICHEROS (ADMIN)
# =========================================================

@user_passes_test(is_admin)
def cargar_fichero(request):
    return render(request, "cargar_fichero.html")


@user_passes_test(is_admin)
def subir_fichero(request):

    # -----------------------------------------------------
    # VALIDAR PETICIÓN
    # -----------------------------------------------------
    if request.method == "POST" and request.FILES.get("fichero"):

        fichero = request.FILES["fichero"]
        nombre = fichero.name.lower()

        try:

            # -------------------------------------------------
            # IMPORTAR JSON
            # -------------------------------------------------
            if nombre.endswith(".json"):

                data = json.load(fichero)

                for doc in data:
                    doc.pop("_id", None)

                dogs_col.insert_many(data)
                messages.success(request, f"JSON cargado ({len(data)} registros).")


            # -------------------------------------------------
            # IMPORTAR CSV
            # -------------------------------------------------
            elif nombre.endswith(".csv"):

                contenido = fichero.read().decode("utf-8").splitlines()
                reader = csv.DictReader(contenido)

                data = []

                for row in reader:
                    clean = {}

                    for k, v in row.items():
                        if isinstance(v, str):
                            v = v.strip()

                        if k == "code":
                            v = int(v)

                        clean[k] = v

                    data.append(clean)

                dogs_col.insert_many(data)
                messages.success(request, f"CSV cargado ({len(data)} registros).")


            # -------------------------------------------------
            # FORMATO NO VÁLIDO
            # -------------------------------------------------
            else:
                messages.error(request, "Formato no válido (CSV o JSON).")

        except Exception as e:
            messages.error(request, f"Error: {e}")

    return redirect("cargar_fichero")


# =========================================================
# CATEGORÍAS (ADMIN - MONGO)
# =========================================================

@user_passes_test(is_admin)
def categorias_list(request):

    categorias = []

    for cat in categories_col.find():
        categorias.append({
            "id": str(cat["_id"]),
            "name": cat["name"],
            "slug": cat.get("slug")
        })

    return render(
        request,
        "categorias/list.html",
        {
            "categorias": categorias
        }
    )


# =========================================================
# CREAR CATEGORÍA
# =========================================================

@user_passes_test(is_admin)
def categoria_create(request):

    if request.method == "POST":

        name = request.POST.get("name")

        if name:
            slug = name.lower().replace(" ", "_")

            categories_col.insert_one({
                "name": name,
                "slug": slug
            })

        return redirect("categorias_list")

    return render(request, "categorias/form.html")


# =========================================================
# CATEGORÍAS – MOSTRAR VALORES
# =========================================================

@user_passes_test(is_admin)
def category_values_list(request, category_id):

    # -----------------------------------------------------
    # BUSCAR CATEGORÍA
    # -----------------------------------------------------
    category_doc = categories_col.find_one({"_id": ObjectId(category_id)})

    if not category_doc:
        return redirect("categorias_list")

    category = {
        "id": str(category_doc["_id"]),
        "name": category_doc["name"],
        "slug": category_doc.get("slug")
    }

    # -----------------------------------------------------
    # BUSCAR VALORES ASOCIADOS
    # -----------------------------------------------------
    values = []

    for v in category_values_col.find({"category_slug": category["slug"]}):
        values.append({
            "id": str(v["_id"]),
            "value": v["value"]
        })

    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------
    return render(
        request,
        "categorias/values_list.html",
        {
            "category": category,
            "values": values
        }
    )


# =========================================================
# CATEGORÍAS – ACTUALIZAR
# =========================================================

@user_passes_test(is_admin)
def categoria_update(request, category_id):

    # -----------------------------------------------------
    # BUSCAR CATEGORÍA
    # -----------------------------------------------------
    category_doc = categories_col.find_one({"_id": ObjectId(category_id)})

    if not category_doc:
        return redirect("categorias_list")

    categoria = {
        "id": str(category_doc["_id"]),
        "name": category_doc["name"],
        "slug": category_doc.get("slug")
    }

    # -----------------------------------------------------
    # ACTUALIZAR (POST)
    # -----------------------------------------------------
    if request.method == "POST":

        name = request.POST.get("name")

        if name:
            slug = name.lower().replace(" ", "_")

            categories_col.update_one(
                {"_id": ObjectId(category_id)},
                {"$set": {"name": name, "slug": slug}}
            )

        return redirect("categorias_list")

    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------
    return render(
        request,
        "categorias/form.html",
        {"categoria": categoria}
    )


# =========================================================
# CATEGORÍAS – BORRAR
# =========================================================

@user_passes_test(is_admin)
def categoria_delete(request, category_id):

    # -----------------------------------------------------
    # BUSCAR CATEGORÍA
    # -----------------------------------------------------
    category_doc = categories_col.find_one({"_id": ObjectId(category_id)})

    if category_doc:

        # -------------------------------------------------
        # BORRAR VALORES ASOCIADOS
        # -------------------------------------------------
        category_values_col.delete_many(
            {"category_slug": category_doc.get("slug")}
        )

        # -------------------------------------------------
        # BORRAR CATEGORÍA
        # -------------------------------------------------
        categories_col.delete_one(
            {"_id": ObjectId(category_id)}
        )

    return redirect("categorias_list")


# =========================================================
# VALORES DE CATEGORÍA – CREAR
# =========================================================

@user_passes_test(is_admin)
def category_value_create(request, category_id):

    # -----------------------------------------------------
    # BUSCAR CATEGORÍA
    # -----------------------------------------------------
    category_doc = categories_col.find_one({"_id": ObjectId(category_id)})

    if not category_doc:
        return redirect("categorias_list")

    category = {
        "id": str(category_doc["_id"]),
        "name": category_doc["name"],
        "slug": category_doc.get("slug")
    }

    # -----------------------------------------------------
    # CREAR VALOR (POST)
    # -----------------------------------------------------
    if request.method == "POST":

        value = request.POST.get("value")

        if value:
            category_values_col.insert_one({
                "category_slug": category["slug"],
                "value": value
            })

        return redirect("category_values_list", category_id=category["id"])

    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------
    return render(
        request,
        "categorias/value_form.html",
        {
            "category": category
        }
    )


# =========================================================
# VALORES DE CATEGORÍA – BORRAR
# =========================================================

@user_passes_test(is_admin)
def category_value_delete(request, value_id):

    # -----------------------------------------------------
    # CONEXIÓN DIRECTA A MONGO (LOCAL)
    # -----------------------------------------------------
    client = MongoClient("mongodb://localhost:27017/")
    db = client["dogs"]
    values_col = db["category_values"]

    # -----------------------------------------------------
    # BUSCAR Y BORRAR VALOR
    # -----------------------------------------------------
    value = values_col.find_one({"_id": ObjectId(value_id)})
    values_col.delete_one({"_id": ObjectId(value_id)})

    # -----------------------------------------------------
    # BUSCAR CATEGORÍA PARA REDIRECCIÓN
    # -----------------------------------------------------
    category = categories_col.find_one(
        {"slug": value["category_slug"]}
    )

    return redirect(
        "category_values_list",
        category_id=str(category["_id"])
    )


# =========================================================
# VALORES DE CATEGORÍA – EDITAR
# =========================================================

@user_passes_test(is_admin)
def category_value_update(request, value_id):

    # -----------------------------------------------------
    # BUSCAR VALOR
    # -----------------------------------------------------
    value_doc = category_values_col.find_one({"_id": ObjectId(value_id)})

    if not value_doc:
        return redirect("categorias_list")

    # -----------------------------------------------------
    # ACTUALIZAR (POST)
    # -----------------------------------------------------
    if request.method == "POST":

        new_value = request.POST.get("value")

        if new_value:
            category_values_col.update_one(
                {"_id": ObjectId(value_id)},
                {"$set": {"value": new_value}}
            )

        # volver a la lista de valores de su categoría
        category = categories_col.find_one(
            {"slug": value_doc["category_slug"]}
        )

        return redirect(
            "category_values_list",
            category_id=str(category["_id"])
        )

    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------
    return render(
        request,
        "categorias/value_form.html",
        {
            "value_obj": {
                "id": str(value_doc["_id"]),
                "value": value_doc["value"]
            }
        }
    )



# =========================================================
# ADMIN – LISTAR ELEMENTOS
# =========================================================

@user_passes_test(is_admin)
def admin_elementos_list(request):

    # -----------------------------------------------------
    # OBTENER PERROS ORDENADOS POR CÓDIGO
    # -----------------------------------------------------
    perros = list(dogs_col.find({}, {"_id": 0}).sort("code", 1))

    return render(
        request,
        "admin/elementos_list.html",
        {"perros": perros}
    )


# =========================================================
# ADMIN – CREAR ELEMENTO
# =========================================================

@user_passes_test(is_admin)
def admin_elemento_create(request):

    # -----------------------------------------------------
    # CREAR (POST)
    # -----------------------------------------------------
    if request.method == "POST":

        name = request.POST.get("name")
        image_url = request.POST.get("image_url")
        origin = request.POST.get("origin")
        breed_group = request.POST.get("breed_group")
        life_span_category = request.POST.get("life_span_category")

        # Generar nuevo código automático
        last_dog = dogs_col.find_one(sort=[("code", -1)])
        new_code = last_dog["code"] + 1 if last_dog else 1

        dogs_col.insert_one({
            "code": new_code,
            "name": name,
            "image_url": image_url,
            "origin": origin,
            "breed_group": breed_group,
            "life_span_category": life_span_category,
            "temperaments": []
        })

        messages.success(request, "Elemento creado correctamente.")
        return redirect("admin_elementos_list")

    return render(request, "admin/elemento_form.html")




# =========================================================
# ADMIN – EDITAR ELEMENTO
# =========================================================

@user_passes_test(is_admin)
def admin_elemento_update(request, code):

    # -----------------------------------------------------
    # BUSCAR ELEMENTO
    # -----------------------------------------------------
    perro = dogs_col.find_one({"code": int(code)})

    if not perro:
        messages.error(request, "Elemento no encontrado.")
        return redirect("admin_elementos_list")

    # -----------------------------------------------------
    # ACTUALIZAR (POST)
    # -----------------------------------------------------
    if request.method == "POST":

        name = request.POST.get("name")
        image_url = request.POST.get("image_url")
        origin = request.POST.get("origin")
        breed_group = request.POST.get("breed_group")
        life_span_category = request.POST.get("life_span_category")

        dogs_col.update_one(
            {"code": int(code)},
            {
                "$set": {
                    "name": name,
                    "image_url": image_url,
                    "origin": origin,
                    "breed_group": breed_group,
                    "life_span_category": life_span_category
                }
            }
        )

        messages.success(request, "Elemento actualizado correctamente.")
        return redirect("admin_elementos_list")

    return render(
        request,
        "admin/elemento_form.html",
        {
            "perro": perro
        }
    )


# =========================================================
# ADMIN – ELIMINAR ELEMENTO
# =========================================================

@user_passes_test(is_admin)
def admin_elemento_delete(request, code):

    dogs_col.delete_one({"code": int(code)})

    messages.success(request, "Elemento eliminado correctamente.")
    return redirect("admin_elementos_list")


# =========================================================
# RANKINGS – CREAR
# =========================================================

@login_required
def create_ranking(request):

    # -----------------------------------------------------
    # CREAR (POST)
    # -----------------------------------------------------
    if request.method == "POST":

        name = request.POST.get("name")
        category_slug = request.POST.get("category_slug")
        category_value = request.POST.get("category_value")

        if not name:
            messages.error(request, "Debes indicar nombre.")
            return redirect("create_ranking")

        # Comprobar si ya existe ranking para esta categoría y usuario
        existing_ranking = rankings_col.find_one({
            "user_id": request.user.id,
            "category_slug": category_slug if category_slug else None
        })

        if existing_ranking:
            messages.error(
                request,
                "Ya tienes un ranking creado para esta categoría."
            )
            return redirect("create_ranking")

        rankings_col.insert_one({
            "user_id": request.user.id,
            "name": name,
            "category_slug": category_slug if category_slug else None,
            "category_value": category_value if category_value else None,
            "dogs": []
        })

        return redirect("my_rankings")


    # -----------------------------------------------------
    # GET – CARGAR CATEGORÍAS Y VALORES
    # -----------------------------------------------------

    categorias = list(
        categories_col.find({}, {"_id": 0, "slug": 1, "name": 1})
    )

    # valores agrupados por categoría
    valores_por_categoria = {}

    for v in category_values_col.find({}, {"_id": 0, "category_slug": 1, "value": 1}):
        slug = v["category_slug"]

        if slug not in valores_por_categoria:
            valores_por_categoria[slug] = []

        valores_por_categoria[slug].append(v["value"])

    return render(
        request,
        "rankings/create.html",
        {
            "categorias": categorias,
            "valores_por_categoria": valores_por_categoria
        }
    )


# =========================================================
# RANKINGS – LISTAR MIS RANKINGS
# =========================================================

@login_required
def my_rankings(request):

    rankings = []

    for r in rankings_col.find({"user_id": request.user.id}):
        rankings.append({
            "id": str(r["_id"]),
            "name": r["name"],
            "total_dogs": len(r.get("dogs", []))
        })

    return render(
        request,
        "rankings/list.html",
        {
            "rankings": rankings
        }
    )


# =========================================================
# RANKINGS – AÑADIR PERRO
# =========================================================

@login_required
def add_to_ranking(request, code):

    # -----------------------------------------------------
    # VALIDAR METODO
    # -----------------------------------------------------
    if request.method != "POST":
        return redirect("my_rankings")

    ranking_id = request.POST.get("ranking_id")

    # -----------------------------------------------------
    # BUSCAR RANKING DEL USUARIO
    # -----------------------------------------------------
    ranking = rankings_col.find_one({
        "_id": ObjectId(ranking_id),
        "user_id": request.user.id
    })

    if not ranking:
        messages.error(request, "Ranking no encontrado o no autorizado.")
        return redirect("my_rankings")


    # -----------------------------------------------------
    # COMPROBAR QUE EL PERRO EXISTE
    # -----------------------------------------------------
    perro = dogs_col.find_one({"code": int(code)}, {"_id": 0})

    if not perro:
        messages.error(request, "Perro no encontrado.")
        return redirect("editar_ranking", ranking_id=ranking_id)


    # -----------------------------------------------------
    # SI EL RANKING TIENE GRUPO, VALIDAR COINCIDENCIA
    # -----------------------------------------------------
    if ranking.get("group"):
        if perro.get("breed_group") != ranking.get("group"):
            messages.error(request, "Este perro no pertenece al grupo del ranking.")
            return redirect("editar_ranking", ranking_id=ranking_id)


    # -----------------------------------------------------
    # COMPROBAR QUE EL USUARIO LO HA VALORADO
    # -----------------------------------------------------
    user_rating = ratings_col.find_one({
        "user_id": request.user.id,
        "dog_code": int(code)
    })

    if not user_rating:
        messages.error(request, "Solo puedes añadir perros que hayas valorado.")
        return redirect("editar_ranking", ranking_id=ranking_id)


    # -----------------------------------------------------
    # LIMITAR A MÁXIMO 10
    # -----------------------------------------------------
    if len(ranking.get("dogs", [])) >= 10:
        messages.warning(request, "Máximo 10 perros por ranking.")
        return redirect("editar_ranking", ranking_id=ranking_id)


    # -----------------------------------------------------
    # EVITAR DUPLICADOS
    # -----------------------------------------------------
    already_exists = any(
        dog["dog_code"] == int(code)
        for dog in ranking.get("dogs", [])
    )

    if already_exists:
        return redirect("editar_ranking", ranking_id=ranking_id)


    # -----------------------------------------------------
    # INSERTAR EN EL RANKING
    # -----------------------------------------------------
    position = len(ranking.get("dogs", [])) + 1

    rankings_col.update_one(
        {"_id": ObjectId(ranking_id)},
        {
            "$push": {
                "dogs": {
                    "dog_code": int(code),
                    "position": position
                }
            }
        }
    )

    return redirect(f"/ranking/{ranking_id}/editar/#dog-{code}")


# =========================================================
# RANKING – DETALLE (USUARIO)
# =========================================================

@login_required
def ranking_detail(request, ranking_id):

    # -----------------------------------------------------
    # BUSCAR RANKING DEL USUARIO
    # -----------------------------------------------------
    ranking = rankings_col.find_one({
        "_id": ObjectId(ranking_id),
        "user_id": request.user.id
    })

    if not ranking:
        return redirect("my_rankings")

    dogs = []

    # -----------------------------------------------------
    # ORDENAR PERROS POR POSICIÓN
    # -----------------------------------------------------
    sorted_dogs = sorted(
        ranking.get("dogs", []),
        key=lambda x: x.get("position", 0)
    )

    # -----------------------------------------------------
    # OBTENER DATOS COMPLETOS DE CADA PERRO
    # -----------------------------------------------------
    for item in sorted_dogs:
        dog = dogs_col.find_one(
            {"code": item["dog_code"]},
            {"_id": 0}
        )
        if dog:
            dogs.append(dog)

    # -----------------------------------------------------
    # CONTEXTO
    # -----------------------------------------------------
    context = {
        "ranking": ranking,
        "dogs": dogs,
        "group": ranking.get("group")
    }

    return render(
        request,
        "rankings/detail.html",
        context
    )


# =========================================================
# RANKING – POR GRUPO
# =========================================================

def ranking_por_grupo(request, group_name):

    # -----------------------------------------------------
    # OBTENER PERROS DEL GRUPO
    # -----------------------------------------------------
    dogs = list(dogs_col.find(
        {"breed_group": group_name},
        {"_id": 0}
    ))

    if not dogs:
        return render(request, "ranking_global.html", {
            "group_name": group_name,
            "ranking": []
        })

    dog_codes = [dog["code"] for dog in dogs]

    # -----------------------------------------------------
    # CALCULAR MEDIAS CON AGREGACIÓN
    # -----------------------------------------------------
    ranking = list(ratings_col.aggregate([
        {
            "$match": {
                "dog_code": {"$in": dog_codes}
            }
        },
        {
            "$group": {
                "_id": "$dog_code",
                "avg_score": {"$avg": "$score"},
                "total": {"$sum": 1}
            }
        },
        {"$sort": {"avg_score": -1}}
    ]))

    # -----------------------------------------------------
    # MAPA CODE -> NOMBRE
    # -----------------------------------------------------
    dog_map = {dog["code"]: dog["name"] for dog in dogs}

    for item in ranking:
        item["dog_code"] = item["_id"]
        item["name"] = dog_map.get(item["_id"], "Desconocido")

    return render(request, "ranking_global.html", {
        "group_name": group_name,
        "ranking": ranking
    })



# =========================================================
# RANKING – GLOBAL CON FILTROS
# =========================================================

def ranking_global(request):

    group = request.GET.get("group")
    origin = request.GET.get("origin")
    life = request.GET.get("life")

    # -----------------------------------------------------
    # FILTRO BASE PARA PERROS
    # -----------------------------------------------------
    dog_query = {}

    if group:
        dog_query["breed_group"] = group

    if origin:
        dog_query["origin"] = origin

    if life:
        dog_query["life_span_category"] = life

    # -----------------------------------------------------
    # OBTENER PERROS FILTRADOS
    # -----------------------------------------------------
    filtered_dogs = list(
        dogs_col.find(dog_query, {"_id": 0, "code": 1, "name": 1})
    )

    if not filtered_dogs:
        return render(request, "rankings/ranking_global.html", {
            "ranking": [],
            "titulo": "Ranking Global"
        })

    dog_codes = [dog["code"] for dog in filtered_dogs]

    # -----------------------------------------------------
    # AGREGACIÓN EN RATINGS
    # -----------------------------------------------------
    pipeline = [
        {"$match": {"dog_code": {"$in": dog_codes}}},
        {
            "$group": {
                "_id": "$dog_code",
                "avg_score": {"$avg": "$score"},
                "total": {"$sum": 1}
            }
        },
        {"$sort": {"avg_score": -1}}
    ]

    stats = list(ratings_col.aggregate(pipeline))

    # -----------------------------------------------------
    # MAPA CODE -> NAME
    # -----------------------------------------------------
    name_map = {
        dog["code"]: dog["name"]
        for dog in filtered_dogs
    }

    ranking = []
    position = 1

    # -----------------------------------------------------
    # CONSTRUIR RANKING FINAL
    # -----------------------------------------------------
    for stat in stats:
        ranking.append({
            "position": position,
            "name": name_map.get(stat["_id"], "Desconocido"),
            "avg_score": round(stat["avg_score"], 2),
            "total": stat["total"]
        })
        position += 1

    # -----------------------------------------------------
    # CONSTRUIR TÍTULO DINÁMICO
    # -----------------------------------------------------
    titulo = "Ranking Global"

    if group:
        titulo += f" - Grupo: {group}"
    if origin:
        titulo += f" - Origen: {origin}"
    if life:
        titulo += f" - Vida: {life}"

    return render(request, "rankings/ranking_global.html", {
        "ranking": ranking,
        "titulo": titulo
    })


# =========================================================
# RANKING – POR CATEGORÍA (GRUPO)
# =========================================================
def ranking_categoria(request, group_name):

    # -----------------------------------------------------
    # BUSCAR PERROS DEL GRUPO
    # -----------------------------------------------------
    perros_grupo = list(dogs_col.find(
        {"breed_group": group_name},
        {"_id": 0, "code": 1, "name": 1, "image_url": 1}
    ))

    codigos = [p["code"] for p in perros_grupo]

    # -----------------------------------------------------
    # CALCULAR MEDIA SOLO DE ESOS PERROS
    # -----------------------------------------------------
    ranking = list(ratings_col.aggregate([
        {
            "$match": {
                "dog_code": {"$in": codigos}
            }
        },
        {
            "$group": {
                "_id": "$dog_code",
                "avg_score": {"$avg": "$score"},
                "total": {"$sum": 1}
            }
        },
        {"$sort": {"avg_score": -1}}
    ]))

    # -----------------------------------------------------
    # MAPA DE PERROS (code -> datos)
    # -----------------------------------------------------
    mapa_perros = {p["code"]: p for p in perros_grupo}

    resultado = []

    for r in ranking:
        dog_data = mapa_perros.get(r["_id"])

        if dog_data:
            resultado.append({
                "code": dog_data["code"],
                "name": dog_data["name"],
                "image_url": dog_data.get("image_url"),
                "avg_score": round(r["avg_score"], 2),
                "total": r["total"]
            })

    return render(request, "rankings/ranking_categoria.html", {
        "grupo": group_name,
        "ranking": resultado
    })


# =========================================================
# ESTADÍSTICAS GLOBALES
# =========================================================

def estadisticas_globales(request):

    db = dogs_col.database
    ratings_col = db.ratings
    dogs_collection = db.dogs

    # -----------------------------------------------------
    # FILTRO OPCIONAL POR GRUPO
    # -----------------------------------------------------
    group_filter = request.GET.get("group")

    match_stage = {}

    if group_filter:
        match_stage = {
            "$lookup": {
                "from": "dogs",
                "localField": "dog_code",
                "foreignField": "code",
                "as": "dog"
            }
        }

    # -----------------------------------------------------
    # TOTALES
    # -----------------------------------------------------
    total_perros = dogs_collection.count_documents({})
    total_valoraciones = ratings_col.count_documents({})

    # -----------------------------------------------------
    # MEDIA GLOBAL (O FILTRADA)
    # -----------------------------------------------------
    pipeline_media = []

    if group_filter:
        pipeline_media = [
            {
                "$lookup": {
                    "from": "dogs",
                    "localField": "dog_code",
                    "foreignField": "code",
                    "as": "dog"
                }
            },
            {"$unwind": "$dog"},
            {"$match": {"dog.breed_group": group_filter}},
            {"$group": {"_id": None, "media": {"$avg": "$score"}}}
        ]
    else:
        pipeline_media = [
            {"$group": {"_id": None, "media": {"$avg": "$score"}}}
        ]

    media_data = list(ratings_col.aggregate(pipeline_media))
    media_global = round(media_data[0]["media"], 2) if media_data else 0


    # -----------------------------------------------------
    # TOP 5 MEJOR VALORADOS
    # -----------------------------------------------------
    pipeline_top = []

    if group_filter:
        pipeline_top = [
            {
                "$lookup": {
                    "from": "dogs",
                    "localField": "dog_code",
                    "foreignField": "code",
                    "as": "dog"
                }
            },
            {"$unwind": "$dog"},
            {"$match": {"dog.breed_group": group_filter}},
            {
                "$group": {
                    "_id": "$dog_code",
                    "avg_score": {"$avg": "$score"},
                    "total": {"$sum": 1}
                }
            },
            {"$sort": {"avg_score": -1}},
            {"$limit": 5}
        ]
    else:
        pipeline_top = [
            {
                "$group": {
                    "_id": "$dog_code",
                    "avg_score": {"$avg": "$score"},
                    "total": {"$sum": 1}
                }
            },
            {"$sort": {"avg_score": -1}},
            {"$limit": 5}
        ]

    top_mejor_valorados = list(ratings_col.aggregate(pipeline_top))

    for dog in top_mejor_valorados:
        dog["dog_code"] = dog["_id"]

    codigos = [dog["dog_code"] for dog in top_mejor_valorados]

    # -----------------------------------------------------
    # OBTENER NOMBRES DE LOS PERROS TOP
    # -----------------------------------------------------
    perros_top = list(dogs_collection.find(
        {"code": {"$in": codigos}},
        {"_id": 0, "code": 1, "name": 1}
    ))

    mapa_nombres = {
        perro["code"]: perro["name"]
        for perro in perros_top
    }

    for dog in top_mejor_valorados:
        dog["name"] = mapa_nombres.get(dog["dog_code"], "Sin nombre")


    # -----------------------------------------------------
    # MEDIA POR GRUPO (SI NO HAY FILTRO)
    # -----------------------------------------------------
    media_por_grupo = []

    if not group_filter:

        media_por_grupo = list(ratings_col.aggregate([
            {
                "$lookup": {
                    "from": "dogs",
                    "localField": "dog_code",
                    "foreignField": "code",
                    "as": "dog"
                }
            },
            {"$unwind": "$dog"},
            {
                "$group": {
                    "_id": "$dog.breed_group",
                    "media": {"$avg": "$score"},
                    "total": {"$sum": 1}
                }
            },
            {"$sort": {"media": -1}}
        ]))

        for grupo in media_por_grupo:
            grupo["group_name"] = grupo["_id"]


    # -----------------------------------------------------
    # GRUPOS DISPONIBLES (PARA FILTRO)
    # -----------------------------------------------------
    grupos_disponibles = sorted(
        dogs_collection.distinct("breed_group")
    )


    # -----------------------------------------------------
    # CONTEXTO FINAL
    # -----------------------------------------------------
    context = {
        "total_perros": total_perros,
        "total_valoraciones": total_valoraciones,
        "media_global": media_global,
        "top_mejor_valorados": top_mejor_valorados,
        "media_por_grupo": media_por_grupo,
        "grupos_disponibles": grupos_disponibles,
        "group_filter": group_filter
    }

    return render(request, "estadisticas.html", context)


# =========================================================
# PANEL ADMIN
# =========================================================

def panel_admin(request):

    # -----------------------------------------------------
    # VERIFICAR ACCESO SOLO ADMIN
    # -----------------------------------------------------
    if not request.user.is_authenticated or request.user.role != "admin":
        messages.error(request, "Acceso no autorizado.")
        return redirect("inicio")

    db = dogs_col.database
    ratings_col = db.ratings
    dogs_collection = db.dogs
    category_values_col = db.category_values

    # -----------------------------------------------------
    # ESTADÍSTICAS GENERALES
    # -----------------------------------------------------
    total_perros = dogs_collection.count_documents({})
    total_valoraciones = ratings_col.count_documents({})
    total_categorias = category_values_col.count_documents({})
    total_usuarios = User.objects.count()

    # -----------------------------------------------------
    # ÚLTIMOS USUARIOS REGISTRADOS
    # -----------------------------------------------------
    ultimos_usuarios = User.objects.order_by("-id")[:5]

    # -----------------------------------------------------
    # ÚLTIMAS VALORACIONES
    # -----------------------------------------------------
    ultimas_valoraciones = list(
        ratings_col.find().sort("_id", -1).limit(5)
    )

    # Obtener IDs únicos
    dog_codes = list({r["dog_code"] for r in ultimas_valoraciones})
    user_ids = list({r["user_id"] for r in ultimas_valoraciones})

    # Buscar perros
    perros = list(dogs_collection.find(
        {"code": {"$in": dog_codes}},
        {"_id": 0, "code": 1, "name": 1}
    ))
    mapa_perros = {p["code"]: p["name"] for p in perros}

    # Buscar usuarios
    usuarios = User.objects.filter(id__in=user_ids)
    mapa_usuarios = {u.id: u.username for u in usuarios}

    # Añadir nombres a cada valoración
    for r in ultimas_valoraciones:
        r["dog_name"] = mapa_perros.get(r["dog_code"], "Desconocido")
        r["username"] = mapa_usuarios.get(r["user_id"], "Desconocido")

    # -----------------------------------------------------
    # CONTEXTO FINAL
    # -----------------------------------------------------
    context = {
        "total_perros": total_perros,
        "total_valoraciones": total_valoraciones,
        "total_categorias": total_categorias,
        "total_usuarios": total_usuarios,
        "ultimos_usuarios": ultimos_usuarios,
        "ultimas_valoraciones": ultimas_valoraciones,
    }

    return render(request, "panel_admin.html", context)


# =========================================================
# EDITAR RANKING
# =========================================================

@login_required
def editar_ranking(request, ranking_id):

    # -----------------------------------------------------
    # BUSCAR RANKING DEL USUARIO
    # -----------------------------------------------------
    ranking = rankings_col.find_one({
        "_id": ObjectId(ranking_id),
        "user_id": request.user.id
    })

    if not ranking:
        messages.error(request, "Ranking no encontrado.")
        return redirect("my_rankings")

    # -----------------------------------------------------
    # OBTENER PERROS VALORADOS POR EL USUARIO
    # -----------------------------------------------------
    user_ratings = list(ratings_col.find(
        {"user_id": request.user.id},
        {"dog_code": 1, "_id": 0}
    ))

    rated_codes = [r["dog_code"] for r in user_ratings]

    # -----------------------------------------------------
    # FILTRO BASE
    # -----------------------------------------------------
    query = {"code": {"$in": rated_codes}}

    #NUEVO: aplicar filtro si ranking tiene categoría
    if ranking.get("category_slug") and ranking.get("category_value"):

        slug = ranking["category_slug"]
        value = ranking["category_value"]

        if slug == "origen":
            query["origin"] = value

        elif slug == "grupo":
            query["breed_group"] = value

        elif slug == "esperanza_de_vida":
            query["life_span"] = {
                "$regex": f"^{value}"
            }

        elif slug == "temperamento":
            query["temperament"] = {
                "$regex": value,
                "$options": "i"
            }

    # Traer perros filtrados
    perros = list(dogs_col.find(query, {"_id": 0}))

    # -----------------------------------------------------
    # MAPEAR NOMBRES PARA LOS YA AÑADIDOS
    # -----------------------------------------------------
    dog_codes_ranking = [
        item["dog_code"]
        for item in ranking.get("dogs", [])
    ]

    dogs_data = list(dogs_col.find(
        {"code": {"$in": dog_codes_ranking}},
        {"_id": 0, "code": 1, "name": 1}
    ))

    dog_map = {dog["code"]: dog["name"] for dog in dogs_data}

    for item in ranking.get("dogs", []):
        item["name"] = dog_map.get(item["dog_code"], "Desconocido")

    # -----------------------------------------------------
    # CONTEXTO
    # -----------------------------------------------------
    context = {
        "ranking": ranking,
        "ranking_id": str(ranking["_id"]),
        "perros": perros,
        "dog_codes_in_ranking": dog_codes_ranking
    }

    return render(request, "rankings/editar_ranking.html", context)


# =========================================================
# ELIMINAR DEL RANKING
# =========================================================

@login_required
def remove_from_ranking(request, code):

    if request.method == "POST":

        ranking_id = request.POST.get("ranking_id")

        ranking = rankings_col.find_one({
            "_id": ObjectId(ranking_id)
        })

        if ranking and ranking["user_id"] == request.user.id:

            # Eliminar el perro
            rankings_col.update_one(
                {"_id": ObjectId(ranking_id)},
                {
                    "$pull": {
                        "dogs": {"dog_code": int(code)}
                    }
                }
            )

            # Obtener ranking actualizado
            ranking_updated = rankings_col.find_one({
                "_id": ObjectId(ranking_id)
            })

            dogs = ranking_updated.get("dogs", [])

            # Recalcular posiciones
            for index, dog in enumerate(dogs, start=1):
                dog["position"] = index

            # Guardar nueva lista ordenada
            rankings_col.update_one(
                {"_id": ObjectId(ranking_id)},
                {"$set": {"dogs": dogs}}
            )

        return redirect(f"/ranking/{ranking_id}/editar/#dog-{code}")

    return redirect("my_rankings")


# =========================================================
# ELIMINAR RANKING
# =========================================================

@login_required
def delete_ranking(request, ranking_id):

    ranking = rankings_col.find_one({
        "_id": ObjectId(ranking_id),
        "user_id": request.user.id
    })

    if ranking:
        rankings_col.delete_one({"_id": ObjectId(ranking_id)})

    return redirect("my_rankings")


# =========================================================
# ACTUALIZAR ORDEN RANKING (AJAX)
# =========================================================

@login_required
def update_ranking_order(request, ranking_id):

    if request.method == "POST":

        ranking = rankings_col.find_one({
            "_id": ObjectId(ranking_id),
            "user_id": request.user.id
        })

        if not ranking:
            return JsonResponse({"error": "No autorizado"}, status=403)

        data = json.loads(request.body)
        new_order = data.get("order", [])

        updated_dogs = []

        for index, dog_code in enumerate(new_order):
            updated_dogs.append({
                "dog_code": int(dog_code),
                "position": index + 1
            })

        rankings_col.update_one(
            {"_id": ObjectId(ranking_id)},
            {"$set": {"dogs": updated_dogs}}
        )

        return JsonResponse({"status": "ok"})

    return JsonResponse({"error": "Invalid request"}, status=400)

