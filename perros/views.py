from django.http import JsonResponse
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['dogs']
collection = db['dogs']


def listar_perros (request):
    perros = list(collection.find({},{"_id":0}))
    return JsonResponse(perros, safe=False)