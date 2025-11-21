from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import Restaurant, MenuItem, Order, OrderItem, Delivery

User = get_user_model()


# PUBLIC_INTERFACE
class UserRegisterSerializer(serializers.ModelSerializer):
    """Register a new user with username, email and password."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


# PUBLIC_INTERFACE
class LoginSerializer(serializers.Serializer):
    """Authenticate user by username and password, returns a simple success flag."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs.get("username"), password=attrs.get("password"))
        if not user:
            raise serializers.ValidationError(_("Invalid credentials"))
        attrs["user"] = user
        return attrs


# PUBLIC_INTERFACE
class RestaurantSerializer(serializers.ModelSerializer):
    """Serializer for Restaurant objects."""
    class Meta:
        model = Restaurant
        fields = ("id", "name", "description", "address", "is_active", "created_at", "updated_at")


# PUBLIC_INTERFACE
class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for MenuItem objects."""
    restaurant_id = serializers.PrimaryKeyRelatedField(
        source="restaurant", queryset=Restaurant.objects.all(), write_only=True
    )
    restaurant = RestaurantSerializer(read_only=True)

    class Meta:
        model = MenuItem
        fields = (
            "id",
            "restaurant",
            "restaurant_id",
            "name",
            "description",
            "price",
            "is_available",
            "created_at",
            "updated_at",
        )


class OrderItemReadSerializer(serializers.ModelSerializer):
    """Read serializer for OrderItem with nested menu item."""
    menu_item = MenuItemSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "menu_item", "quantity", "unit_price")


class OrderItemWriteSerializer(serializers.ModelSerializer):
    """Write serializer for OrderItem using menu_item id."""
    menu_item_id = serializers.PrimaryKeyRelatedField(
        source="menu_item", queryset=MenuItem.objects.filter(is_available=True), write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ("menu_item_id", "quantity", "unit_price")

    def validate(self, attrs):
        menu_item = attrs["menu_item"]
        if not menu_item.is_available:
            raise serializers.ValidationError("Selected menu item is not available.")
        if attrs.get("quantity", 0) <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return attrs


# PUBLIC_INTERFACE
class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order. Uses nested items on create."""
    items = OrderItemReadSerializer(many=True, read_only=True)
    restaurant_id = serializers.PrimaryKeyRelatedField(
        source="restaurant", queryset=Restaurant.objects.filter(is_active=True), write_only=True
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "customer",
            "restaurant",
            "restaurant_id",
            "status",
            "total_price",
            "delivery_address",
            "notes",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("customer", "restaurant", "status", "total_price", "created_at", "updated_at", "restaurant")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure nested current items are represented
        data["restaurant"] = RestaurantSerializer(instance.restaurant).data
        data["items"] = OrderItemReadSerializer(instance.items.all(), many=True).data
        # Delivery info if available
        delivery = getattr(instance, "delivery", None)
        data["delivery"] = DeliverySerializer(delivery).data if delivery else None
        return data


# PUBLIC_INTERFACE
class OrderCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Order with nested order items."""
    items = OrderItemWriteSerializer(many=True)
    restaurant_id = serializers.PrimaryKeyRelatedField(
        source="restaurant", queryset=Restaurant.objects.filter(is_active=True)
    )

    class Meta:
        model = Order
        fields = ("id", "restaurant_id", "delivery_address", "notes", "items")

    def validate(self, attrs):
        items = self.initial_data.get("items", [])
        if not items:
            raise serializers.ValidationError("Order must contain at least one item.")
        # Validate all menu items belong to the same restaurant
        restaurant = attrs["restaurant"]
        menu_item_ids = [i.get("menu_item_id") for i in items]
        invalid = MenuItem.objects.filter(id__in=menu_item_ids).exclude(restaurant=restaurant).exists()
        if invalid:
            raise serializers.ValidationError("All items must belong to the selected restaurant.")
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        user = self.context["request"].user
        order = Order.objects.create(customer=user, status="pending", **validated_data)
        for item in items_data:
            menu_item = item["menu_item"]
            quantity = item.get("quantity", 1)
            unit_price = item.get("unit_price") or menu_item.price
            OrderItem.objects.create(order=order, menu_item=menu_item, quantity=quantity, unit_price=unit_price)
        # auto-create delivery
        Delivery.objects.create(order=order, status="pending")
        order.recalc_total()
        return order


# PUBLIC_INTERFACE
class DeliverySerializer(serializers.ModelSerializer):
    """Serializer for Delivery model."""
    class Meta:
        model = Delivery
        fields = ("id", "order", "courier", "status", "eta", "current_location", "created_at", "updated_at")
        read_only_fields = ("order", "created_at", "updated_at")
