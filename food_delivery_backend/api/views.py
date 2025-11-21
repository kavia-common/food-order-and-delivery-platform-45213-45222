from django.contrib.auth import get_user_model, login
from django.db.models import Q
from rest_framework import viewsets, mixins, status, permissions, pagination
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Restaurant, MenuItem, Order, Delivery
from .serializers import (
    UserRegisterSerializer,
    LoginSerializer,
    RestaurantSerializer,
    MenuItemSerializer,
    OrderSerializer,
    OrderCreateSerializer,
    DeliverySerializer,
)
from .permissions import CanManageOrderStatus, CanManageDeliveryStatus

User = get_user_model()


class DefaultPagination(pagination.PageNumberPagination):
    """Default pagination for list endpoints"""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@api_view(['GET'])
def health(request):
    """
    Health check endpoint.
    Returns a simple JSON payload indicating the server is up.
    """
    return Response({"message": "Server is up!"})


# PUBLIC_INTERFACE
class RegisterView(APIView):
    """
    Register a new user.
    POST: {username, email, password} -> 201 Created
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"id": user.id, "username": user.username, "email": user.email}, status=status.HTTP_201_CREATED)


# PUBLIC_INTERFACE
class LoginView(APIView):
    """
    Login a user using session authentication.
    POST: {username, password} -> 200 OK
    Note: For simplicity, this sets a session cookie. In production, use JWT or token auth.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response({"detail": "Login successful"})


# PUBLIC_INTERFACE
class RestaurantViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    list:
      summary: List restaurants
      description: Returns a paginated list of active restaurants. Supports search by name or description.
    retrieve:
      summary: Retrieve a restaurant
      description: Returns a single restaurant by id.
    """
    queryset = Restaurant.objects.filter(is_active=True).order_by("name")
    serializer_class = RestaurantSerializer
    pagination_class = DefaultPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return qs

    @action(methods=["get"], detail=True, url_path="menu", permission_classes=[permissions.AllowAny])
    def menu(self, request, pk=None):
        """Get menu items for this restaurant."""
        restaurant = self.get_object()
        items = restaurant.menu_items.filter(is_available=True).order_by("name")
        page = self.paginate_queryset(items)
        serializer = MenuItemSerializer(page or items, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


# PUBLIC_INTERFACE
class MenuItemViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    list:
      summary: List menu items
      description: Returns a paginated list of available menu items; filter by restaurant_id.
    retrieve:
      summary: Retrieve menu item
      description: Returns a single menu item by id.
    """
    serializer_class = MenuItemSerializer
    pagination_class = DefaultPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = MenuItem.objects.filter(is_available=True).select_related("restaurant").order_by("name")
        rid = self.request.query_params.get("restaurant_id")
        if rid:
            qs = qs.filter(restaurant_id=rid)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return qs


# PUBLIC_INTERFACE
class OrderViewSet(viewsets.ModelViewSet):
    """
    list:
      summary: List user's orders
      description: Customers see their orders; staff can see all orders.
    create:
      summary: Create a new order
      description: Creates an order with nested items; auto-creates a Delivery entity.
    retrieve:
      summary: Retrieve order details
      description: Returns order details including items and delivery information.
    partial_update:
      summary: Update order status
      description: Staff/admin can update status; customers cannot modify order status.
    """
    queryset = Order.objects.select_related("restaurant", "customer").prefetch_related("items__menu_item")
    serializer_class = OrderSerializer
    pagination_class = DefaultPagination
    permission_classes = [CanManageOrderStatus]

    def get_queryset(self):
        qs = super().get_queryset().order_by("-created_at")
        user = self.request.user
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return qs
        return qs.filter(customer=user)

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(methods=["get"], detail=True, url_path="status")
    def status(self, request, pk=None):
        """Get current status of an order."""
        order = self.get_object()
        return Response({"order_id": order.id, "status": order.status})

    @action(methods=["patch"], detail=True, url_path="status", permission_classes=[CanManageOrderStatus])
    def update_status(self, request, pk=None):
        """Update order status (staff/admin only)."""
        order = self.get_object()
        new_status = request.data.get("status")
        valid = dict(Order.STATUS_CHOICES).keys()
        if new_status not in valid:
            return Response({"detail": "Invalid status"}, status=400)
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return Response({"order_id": order.id, "status": order.status})


# PUBLIC_INTERFACE
class DeliveryViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    list:
      summary: List deliveries
      description: Staff/admin list all; customers see deliveries for their orders; couriers see assigned deliveries.
    retrieve:
      summary: Retrieve delivery
    partial_update:
      summary: Update delivery status/location
      description: Allowed for staff/admin or assigned courier.
    """
    queryset = Delivery.objects.select_related("order", "order__customer", "order__restaurant", "courier")
    serializer_class = DeliverySerializer
    pagination_class = DefaultPagination
    permission_classes = [CanManageDeliveryStatus]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().order_by("-created_at")
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return qs
        # Courier can see assigned
        courier_qs = qs.filter(courier=user)
        # Customers can see their deliveries
        customer_qs = qs.filter(order__customer=user)
        return (courier_qs | customer_qs).distinct()

    @action(methods=["get"], detail=True, url_path="status", permission_classes=[CanManageDeliveryStatus])
    def status(self, request, pk=None):
        delivery = self.get_object()
        return Response({"delivery_id": delivery.id, "status": delivery.status, "eta": delivery.eta, "location": delivery.current_location})
