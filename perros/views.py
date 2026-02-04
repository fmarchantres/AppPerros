from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from pymongo import MongoClient
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from .models import Category
from django.shortcuts import render, get_object_or_404, redirect
from .models import Category, CategoryValue



import csv
import json

from django.shortcuts import redirect
from django.contrib import messages



from perros.forms import RegistroForm, LoginForm
from perros.models import *

client = MongoClient('mongodb://localhost:27017/')
db = client['dogs']
collection = db['dogs']


#HELPER DE PERMISOS
def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

#LISTAR CATEGORIAS
@user_passes_test(is_admin)
def categorias_list(request):
    categorias = Category.objects.all().order_by('name')
    return render(request, 'categorias/list.html', {'categorias': categorias})

#CREAR CATEGORIA
@user_passes_test(is_admin)
def categoria_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Category.objects.get_or_create(name=name)
        return redirect('categorias_list')
    return render(request, 'categorias/form.html')

#EDITAR CATEGORIA
@user_passes_test(is_admin)
def categoria_update(request, pk):
    categoria = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            categoria.name = name
            categoria.save()
        return redirect('categorias_list')

    return render(request, 'categorias/form.html', {'categoria': categoria})

#ELIMINAR CATEGORIA
@user_passes_test(is_admin)
def categoria_delete(request, pk):
    categoria = get_object_or_404(Category, pk=pk)
    categoria.delete()
    return redirect('categorias_list')

#LISTAR VALORES DE UNA CATEGORIA
@user_passes_test(is_admin)
def category_values_list(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    values = category.values.all().order_by('value')

    return render(
        request,
        'categorias/values_list.html',
        {'category': category, 'values': values}
    )

#CREAR VALOR
@user_passes_test(is_admin)
def category_value_create(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        value = request.POST.get('value')
        if value:
            CategoryValue.objects.get_or_create(
                category=category,
                value=value
            )
        return redirect('category_values_list', category_id=category.id)

    return render(
        request,
        'categorias/value_form.html',
        {'category': category}
    )

#EDITAR VALOR
@user_passes_test(is_admin)
def category_value_update(request, pk):
    value_obj = get_object_or_404(CategoryValue, pk=pk)

    if request.method == 'POST':
        value = request.POST.get('value')
        if value:
            value_obj.value = value
            value_obj.save()
        return redirect(
            'category_values_list',
            category_id=value_obj.category.id
        )

    return render(
        request,
        'categorias/value_form.html',
        {'value_obj': value_obj}
    )

#ELIMINAR VALOR
@user_passes_test(is_admin)
def category_value_delete(request, pk):
    value_obj = get_object_or_404(CategoryValue, pk=pk)
    category_id = value_obj.category.id
    value_obj.delete()
    return redirect('category_values_list', category_id=category_id)


def listar_perros(request):
    perros = list(collection.find({}, {"_id": 0}))
    return JsonResponse(perros, safe=False)


def mostrar_razas(request):
    lista_razas = Raza.objects.all()
    return render(request, 'razas.html')


# @login_required(login_url='login') #PROTECCION AL LOGIN
def inicio(request):
    client = MongoClient("mongodb://localhost:27017/")
    collection = client["dogs"]["dogs"]

    query = {}
    #GRUPO
    group_id = request.GET.get("group")
    if group_id:
        query["group_id"] = int(group_id)

    #ORIGEN
    origin_id = request.GET.get("origin")
    if origin_id:
        query["origin_id"] = int(origin_id)

    # ESPERANZA DE VIDA
    life_id = request.GET.get("life")
    if life_id:
        query["life_span_id"] = int(life_id)

    # TEMPERAMENTO (multi)
    temperament_ids = request.GET.getlist("temperament")
    if temperament_ids:
        query["temperament_ids"] = {"$all": [int(t) for t in temperament_ids]}

    perros = list(collection.find(query, {"_id": 0}))

    # paginación (deja tu lógica actual)
    paginator = Paginator(perros, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # valores de origen
    categoria_origen = Category.objects.get(name__iexact="Origen")
    origenes = CategoryValue.objects.filter(category=categoria_origen).order_by("value")
    categoria_grupo = Category.objects.get(name__iexact="Grupo")
    grupos = CategoryValue.objects.filter(category=categoria_grupo).order_by("value")
    categoria_vida = Category.objects.get(name__iexact="Esperanza de vida")
    vidas = CategoryValue.objects.filter(category=categoria_vida).order_by("value")
    categoria_temp = Category.objects.get(name__iexact="Temperamento")
    temperamentos = CategoryValue.objects.filter(category=categoria_temp).order_by("value")

    return render(request, "inicio.html", {
        "page_obj": page_obj,
        "origenes": origenes,
        "grupos": grupos,
        "vidas": vidas,
        "temperamentos": temperamentos,
    })


def registrar_usuario(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.set_password(form.cleaned_data['password'])
            usuario.save()
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'usuarios/registro.html', {'form': form})


def login_usuario(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            usuario = authenticate(request, username=username, password=password)
            if usuario is not None:
                login(request, usuario)
                return redirect('/')

    else:
        form = LoginForm()
    return render(request, 'usuarios/login.html', {'form': form})


def logout_usuario(request):
    logout(request)
    return redirect('login')


def detalle_perro(request, code):
    perro = collection.find_one({'code': code}, {'_id': 0})

    group = None
    origin = None
    life_span = None
    temperaments = []

    if perro:
        if perro.get('group_id'):
            group = CategoryValue.objects.filter(id=perro['group_id']).first()

        if perro.get('origin_id'):
            origin = CategoryValue.objects.filter(id=perro['origin_id']).first()

        if perro.get('life_span_id'):
            life_span = CategoryValue.objects.filter(id=perro['life_span_id']).first()

        if perro.get('temperament_ids'):
            temperaments = CategoryValue.objects.filter(
                id__in=perro['temperament_ids']
            )

    context = {
        'perro': perro,
        'group': group,
        'origin': origin,
        'life_span': life_span,
        'temperaments': temperaments,
    }

    return render(request, 'detalle_perro.html', context)


#@login_required
def cargar_fichero(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("No autorizado")
    return render(request, "cargar_fichero.html")


def subir_fichero(request):
    if request.method == 'POST' and request.FILES.get("fichero"):
        fichero = request.FILES.get("fichero")
        nombre = fichero.name.lower()
        try:

            client = MongoClient('mongodb://localhost:27017/')
            db = client['dogs']
            collection = db['dogs']

            # JSON
            if nombre.endswith(".json"):
                data = json.load(fichero)
                for doc in data:
                    doc.pop("_id", None)
                collection.insert_many(data)
                total = len(data)
                messages.success(request, f"Fichero JSON leído correctamente ({total} registros).")

                # CSV
            elif nombre.endswith(".csv"):
                contenido = fichero.read().decode("utf-8").splitlines()
                reader = csv.DictReader(contenido)

                data = []
                for row in reader:
                    clean_row = {}
                    for k, v in row.items():
                        if isinstance(v, str):
                            v = v.strip()
                        if k == "code":
                            v = int(v)
                        clean_row[k] = v

                    data.append(clean_row)

                collection.insert_many(data)

                messages.success(
                    request,
                    f"Fichero CSV leído correctamente ({len(data)} registros)."
                )



            else:
                messages.error(
                    request,
                    "Formato no válido. Solo se permiten CSV o JSON."
                )
                return redirect("cargar_fichero")

        except Exception as e:
            messages.error(
                request,
                f"Error al leer el fichero: {e}"
            )

    return redirect("cargar_fichero")
