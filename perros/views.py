from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from pymongo import MongoClient
from django.contrib.auth import authenticate, login, logout

from perros.forms import RegistroForm, LoginForm
from perros.models import *

client = MongoClient('mongodb://localhost:27017/')
db = client['dogs']
collection = db['dogs']


def listar_perros (request):
    perros = list(collection.find({},{"_id":0}))
    return JsonResponse(perros, safe=False)

def mostrar_razas(request):
    lista_razas = Raza.objects.all()
    return render (request, 'razas.html')


@login_required(login_url='login') #PROTECCION AL LOGIN
def inicio(request):
    perros = list(collection.find({},{"_id":0}))
    return render (request, 'inicio.html', {'perros': perros})


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
            usuario = authenticate (request, username=username, password=password)
            if usuario is not None:
                login (request, usuario)
                return redirect('/')

    else:
            form = LoginForm()
    return render(request, 'usuarios/login.html', {'form': form})


def logout_usuario(request):
    logout (request)
    return redirect('login')