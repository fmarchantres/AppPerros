from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from pymongo import MongoClient
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
import csv
import json

from django.shortcuts import redirect
from django.contrib import messages



from perros.forms import RegistroForm, LoginForm
from perros.models import *

client = MongoClient('mongodb://localhost:27017/')
db = client['dogs']
collection = db['dogs']


def listar_perros(request):
    perros = list(collection.find({}, {"_id": 0}))
    return JsonResponse(perros, safe=False)


def mostrar_razas(request):
    lista_razas = Raza.objects.all()
    return render(request, 'razas.html')


# @login_required(login_url='login') #PROTECCION AL LOGIN
def inicio(request):
    # Leemos los perros desde MongoDB
    perros = list(collection.find({}, {"_id": 0}))
    # Creamos el paginador
    paginator = Paginator(perros, 21)

    # Obtenemos la pagina actual
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Enviamos la pagina al template
    return render(request, 'inicio.html', {'page_obj': page_obj})


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
    return render(request, 'detalle_perro.html', {'perro': perro})


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
