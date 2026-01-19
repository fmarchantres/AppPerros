from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

#MODELOS
class UserManager(BaseUserManager):
    def create_user(self, mail, username, role, password=None):
        if not mail or not username or not role:
            raise ValueError("Debes rellenar los campos requeridos (mail, username, role)")
        mail = self.normalize_email(mail)
        user = self.model(mail=mail, username=username, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mail, username, role='admin', password=None):
        user = self.create_user(mail, username, role, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
        ROLES = (
            ('admin', 'Administrador'),
            ('cliente', 'Cliente'),
        )
        mail = models.EmailField(max_length=254, unique=True)
        username = models.CharField(max_length=100, unique=True)
        role = models.CharField(max_length=20, choices=ROLES, default='cliente')
        is_active = models.BooleanField(default=True)
        is_staff = models.BooleanField(default=False)
        objects = UserManager()

        USERNAME_FIELD = 'mail'
        REQUIRED_FIELDS = ['username', 'role']

        def __str__(self):
            return self.username


#MONGODB MODELOS
#RAZA
class Raza(models.Model):
    code = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    breed_group = models.CharField(max_length=50)
    life_span = models.CharField(max_length=50)
    temperament = models.TextField()
    origin = models.CharField(max_length=100)
    image_url = models.URLField(max_length=800)

    class Meta:
        managed = False
        db_table = 'razas'

    def __str__(self):
        return self.name


#VALORACION
class Valoracion (models.Model):
    usuario = models.CharField(max_length=150)
    raza_code = models.IntegerField()
    puntuacion = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True)
    fecha = models.DateField(auto_now=True)

    class Meta:
       managed = False
       db_table = 'valoraciones'


#RANKING
class Ranking (models.Model):
    usuario = models.CharField(max_length=150)
    nombre = models.CharField(max_length=100)


    class Meta:
        managed = False
        db_table = 'rankings'

    def __str__(self):
        return self.nombre