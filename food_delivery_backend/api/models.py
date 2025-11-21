from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base class that adds created/updated timestamps."""
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Restaurant(TimeStampedModel):
    """Represents a restaurant that provides menu items."""
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=512, blank=True)
    is_active = models.BooleanField(default=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_restaurants"
    )

    def __str__(self) -> str:
        return self.name


class MenuItem(TimeStampedModel):
    """Represents a menu item belonging to a restaurant."""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="menu_items")
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ("restaurant", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.restaurant.name})"


class Order(TimeStampedModel):
    """Represents a customer order for items from a single restaurant."""
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("preparing", "Preparing"),
        ("ready", "Ready for Pickup"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_address = models.CharField(max_length=512)
    notes = models.TextField(blank=True)

    def recalc_total(self) -> None:
        total = sum(oi.quantity * oi.unit_price for oi in self.items.all())
        self.total_price = total
        self.save(update_fields=["total_price", "updated_at"])

    def __str__(self) -> str:
        return f"Order #{self.id} - {self.customer} - {self.status}"


class OrderItem(models.Model):
    """Line item within an order that references a MenuItem snapshot."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.unit_price:
            # Snapshot the price from the menu item at time of order item creation
            self.unit_price = self.menu_item.price
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.quantity}x {self.menu_item.name} (Order #{self.order_id})"


class Delivery(TimeStampedModel):
    """Represents the delivery status for an order."""
    STATUS_CHOICES = [
        ("pending", "Pending Assignment"),
        ("assigned", "Assigned"),
        ("picked_up", "Picked up"),
        ("in_transit", "In Transit"),
        ("delivered", "Delivered"),
        ("failed", "Failed"),
    ]
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="delivery")
    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries"
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    eta = models.DateTimeField(null=True, blank=True)
    current_location = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return f"Delivery for Order #{self.order_id} - {self.status}"
