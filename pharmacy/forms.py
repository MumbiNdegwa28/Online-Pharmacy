from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import customuser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = customuser
        fields = ['username', 'email', 'password1', 'password2', 'role']

class CustomAuthenticationForm(AuthenticationForm):
    class Meta:
        model = customuser
        fields = ['username', 'password']
