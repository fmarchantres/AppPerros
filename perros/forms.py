from django import forms
from django.contrib.auth.forms import AuthenticationForm

from perros.models import User


class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ('mail', 'username', 'role', 'password')



class LoginForm (AuthenticationForm):
    username = forms.EmailField (label = 'Correo')
    password = forms.CharField(widget=forms.PasswordInput())