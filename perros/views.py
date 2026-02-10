from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.contrib import messages
from bson import ObjectId
from datetime import datetime
from django.contrib.auth.decorators import login_required
from pymongo import MongoClient
import csv
import json

from perros.forms import RegistroForm, LoginForm
from perros.models import *

# ==============================
# MongoDB
# ==============================
client = MongoClient("mongodb://localhost:27017/")
db = client["dogs"]
dogs_col = db["dogs"]
categories_col = db["categories"]
values_col = db["category_values"]
category_values_col = db["category_values"]
ratings_col = db["ratings"]



# ==============================
# HELPERS
# ==============================
def is_admin(user):
    return user.is_authenticated and user.role == "admin"


# ==============================
# API SIMPLE
# ==============================
def listar_perros(request):
    perros = list(dogs_col.find({}, {"_id": 0}))
    return JsonResponse(perros, safe=False)


# ==============================
# HOME + FILTROS (SOLO MONGO)
# ==============================
def inicio(request):
    query = {}

    origin = request.GET.get("origin")
    group = request.GET.get("group")
    life_span = request.GET.get("life")
    temperament = request.GET.get("temperament")

    if origin:
        query["origin"] = origin

    if group:
        query["breed_group"] = group

    if life_span:
        query["life_span_category"] = life_span

    if temperament:
        query["temperaments"] = temperament  # array → match directo

    perros = list(dogs_col.find(query, {"_id": 0}))

    paginator = Paginator(perros, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Valores únicos para filtros (desde Mongo)
    origenes = sorted(dogs_col.distinct("origin"))
    grupos = sorted(dogs_col.distinct("breed_group"))
    vidas = sorted(dogs_col.distinct("life_span_category"))
    temperamentos = sorted(dogs_col.distinct("temperaments"))

    return render(request, "inicio.html", {
        "page_obj": page_obj,
        "origenes": origenes,
        "grupos": grupos,
        "vidas": vidas,
        "temperamentos": temperamentos,
    })

# ==============================
# VALORACIONES
# ==============================
def get_user_rating(user, dog_code):
    if not user.is_authenticated:
        return None

    return ratings_col.find_one({
        "user_id": user.id,
        "dog_code": dog_code
    })


# ==============================
# DETALLE (SOLO MONGO)
# ==============================
def detalle_perro(request, code):
    perro = dogs_col.find_one({"code": code}, {"_id": 0})

    if not perro:
        return render(request, "404.html", status=404)

    user_rating = get_user_rating(request.user, code)

    return render(request, "detalle_perro.html", {
        "perro": perro,
        "user_rating": user_rating
    })


# ==============================
# VALORACION
# ==============================
#@login_required
def rate_dog(request, code):
    score = int(request.POST.get("score"))
    comment = request.POST.get("comment", "").strip()

    if score < 1 or score > 5:
        return redirect("detalle_perro", code=code)

    existing = ratings_col.find_one({
        "user_id": request.user.id,
        "dog_code": code
    })

    now = datetime.utcnow()

    if existing:
        ratings_col.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "score": score,
                "comment": comment,
                "updated_at": now
            }}
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


# ==============================
# USUARIOS
# ==============================
def registrar_usuario(request):
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
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            usuario = authenticate(request, username=username, password=password)
            if usuario:
                login(request, usuario)
                return redirect("/")
    else:
        form = LoginForm()
    return render(request, "usuarios/login.html", {"form": form})


def logout_usuario(request):
    logout(request)
    return redirect("login")


# ==============================
# CARGA DE FICHEROS (ADMIN)
# ==============================
@user_passes_test(is_admin)
def cargar_fichero(request):
    return render(request, "cargar_fichero.html")


@user_passes_test(is_admin)
def subir_fichero(request):
    if request.method == "POST" and request.FILES.get("fichero"):
        fichero = request.FILES["fichero"]
        nombre = fichero.name.lower()

        try:
            # JSON
            if nombre.endswith(".json"):
                data = json.load(fichero)
                for doc in data:
                    doc.pop("_id", None)
                dogs_col.insert_many(data)
                messages.success(request, f"JSON cargado ({len(data)} registros).")

            # CSV
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

            else:
                messages.error(request, "Formato no válido (CSV o JSON).")

        except Exception as e:
            messages.error(request, f"Error: {e}")

    return redirect("cargar_fichero")

# ==============================
# CATEGORÍAS (ADMIN - MONGO)
# ==============================
#@user_passes_test(is_admin)
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


# ==============================
#        CREAR CATEGORÍAS
# ==============================
#@user_passes_test(is_admin)
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



# ==============================
# CATEGORÍAS MOSTRAR VALORES
# ==============================
#@user_passes_test(is_admin)
def category_values_list(request, category_id):
    # Buscar categoría
    category_doc = categories_col.find_one({"_id": ObjectId(category_id)})

    if not category_doc:
        return redirect("categorias_list")

    category = {
        "id": str(category_doc["_id"]),
        "name": category_doc["name"],
        "slug": category_doc.get("slug")
    }

    # Buscar valores asociados
    values = []
    for v in category_values_col.find({"category_slug": category["slug"]}):
        values.append({
            "id": str(v["_id"]),
            "value": v["value"]
        })

    return render(
        request,
        "categorias/values_list.html",
        {
            "category": category,
            "values": values
        }
    )

# ==============================
#    ACTUALIZAR CATEGORÍAS
# ==============================
#@user_passes_test(is_admin)
def categoria_update(request, category_id):
    category_doc = categories_col.find_one({"_id": ObjectId(category_id)})

    if not category_doc:
        return redirect("categorias_list")

    categoria = {
        "id": str(category_doc["_id"]),
        "name": category_doc["name"],
        "slug": category_doc.get("slug")
    }

    if request.method == "POST":
        name = request.POST.get("name")

        if name:
            slug = name.lower().replace(" ", "_")
            categories_col.update_one(
                {"_id": ObjectId(category_id)},
                {"$set": {"name": name, "slug": slug}}
            )

        return redirect("categorias_list")

    return render(
        request,
        "categorias/form.html",
        {"categoria": categoria}
    )

# ==============================
#     BORRAR CATEGORÍAS
# ==============================

#@user_passes_test(is_admin)
def categoria_delete(request, category_id):
    category_doc = categories_col.find_one({"_id": ObjectId(category_id)})

    if category_doc:
        # borrar valores asociados
        category_values_col.delete_many(
            {"category_slug": category_doc.get("slug")}
        )

        # borrar categoría
        categories_col.delete_one(
            {"_id": ObjectId(category_id)}
        )

    return redirect("categorias_list")

# ==============================
#   CREAR VALORES CATEGORÍAS
# ==============================
#@user_passes_test(is_admin)
def category_value_create(request, category_id):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["dogs"]
    categories_col = db["categories"]
    values_col = db["category_values"]

    category = categories_col.find_one({"_id": ObjectId(category_id)})

    if request.method == "POST":
        value = request.POST.get("value")
        if value:
            values_col.insert_one({
                "category_slug": category["slug"],
                "value": value
            })
        return redirect("category_values_list", category_id=category_id)

    return render(
        request,
        "categorias/value_form.html",
        {"category": category}
    )

# ==============================
#   BORRAR VALORES CATEGORÍAS
# ==============================
#@user_passes_test(is_admin)
def category_value_delete(request, value_id):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["dogs"]
    values_col = db["category_values"]

    value = values_col.find_one({"_id": ObjectId(value_id)})
    values_col.delete_one({"_id": ObjectId(value_id)})

    category = categories_col.find_one(
        {"slug": value["category_slug"]}
    )

    return redirect(
        "category_values_list",
        category_id=str(category["_id"])
    )


# ==============================
#   EDITAR VALORES CATEGORÍAS
# ==============================
#@user_passes_test(is_admin)
def category_value_update(request, value_id):
    value_doc = category_values_col.find_one({"_id": ObjectId(value_id)})

    if not value_doc:
        return redirect("categorias_list")

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
