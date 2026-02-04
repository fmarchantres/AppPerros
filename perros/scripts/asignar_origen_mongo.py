import os
import django
from pymongo import MongoClient

# --- Inicializar Django ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AppPerros.settings')
django.setup()

from perros.models import Category, CategoryValue

# --- Conexión Mongo ---
client = MongoClient("mongodb://localhost:27017/")
db = client["dogs"]
collection = db["dogs"]

# --- Obtener categoría ORIGEN ---
categoria_origen = Category.objects.get(name__iexact="Origen")

# --- Recorrer razas ---
for perro in collection.find():
    origin_text = perro.get("origin")
    if not origin_text:
        continue

    valor = CategoryValue.objects.filter(
        category=categoria_origen,
        value__iexact=origin_text.strip()
    ).first()

    if valor:
        collection.update_one(
            {"_id": perro["_id"]},
            {"$set": {"origin_id": valor.id}}
        )
        print(f"✔ {perro.get('name')} → origin_id = {valor.id}")
    else:
        print(f"✖ NO encontrado en categorías: {origin_text}")
