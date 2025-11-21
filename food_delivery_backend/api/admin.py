from django.contrib import admin
from .models import Restaurant, MenuItem, Order, OrderItem, Delivery


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    search_fields = ("name", "description")


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "restaurant", "price", "is_available")
    list_filter = ("restaurant", "is_available")
    search_fields = ("name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "restaurant", "status", "total_price", "created_at")
    list_filter = ("status", "restaurant")
    search_fields = ("customer__username",)
    inlines = [OrderItemInline]


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "courier", "status", "eta")
    list_filter = ("status",)
