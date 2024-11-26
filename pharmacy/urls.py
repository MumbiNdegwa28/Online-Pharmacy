from django.urls import path
from . import views

app_name = "pharmacy"

urlpatterns = [
    path('', views.home, name="home"),
    path('order/<int:pk>/', views.order_medicine, name='order_medicine'),

    # path('register', views.register, name='register'),
    # path('login', views.login, name='login'),
    # path('logout', views.logout, name='logout'),
]
