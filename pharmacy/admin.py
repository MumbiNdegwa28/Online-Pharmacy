from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import customuser, Medicine, Order


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
    list_display = ('medicine', 'customer_name', 'customer_phone', 'quantity', 'order_date')
    search_fields = ('customer_name', 'customer_phone', 'medicine__name')
    list_filter = ('order_date',)
    ordering = ('-order_date',)
