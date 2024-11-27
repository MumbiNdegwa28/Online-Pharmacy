from django.urls import path
from . import views

app_name = "pharmacy"

urlpatterns = [
    path('', views.home, name="home"),
    path('order/<int:pk>/', views.order_medicine, name='order_medicine'),
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:medicine_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    # path('add-to-cart/<int:medicine_id>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout, name='checkout'),

    # path('register', views.register, name='register'),
    # path('login', views.login, name='login'),
    # path('logout', views.logout, name='logout'),
]
