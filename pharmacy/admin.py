from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import customuser, Medicine, Order, Cart, CartItem, Payment


# Customizing the UserAdmin for customuser
@admin.register(customuser)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Role', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)


# Admin configuration for Medicine model
@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'image')
    search_fields = ('name',)
    list_filter = ('price',)
    ordering = ('name',)


# Admin configuration for Order model
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'customer_name', 'customer_phone', 'quantity', 'order_date', 'status')
    search_fields = ('customer_name', 'customer_phone', 'medicine__name')
    list_filter = ('order_date', 'status')
    ordering = ('-order_date',)


# Admin configuration for Cart model
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_id', 'created_at')
    search_fields = ('user__username', 'session_id')
    list_filter = ('created_at',)
    ordering = ('-created_at',)


# Admin configuration for CartItem model
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'medicine', 'quantity')
    search_fields = ('cart__user__username', 'medicine__name')
    list_filter = ('quantity',)
    ordering = ('cart',)


# Admin configuration for Payment model
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'payment_status', 'payment_method', 'transaction_id', 'payment_date')
    search_fields = ('order__id', 'transaction_id')
    list_filter = ('payment_status', 'payment_method', 'payment_date')
    ordering = ('-payment_date',)
