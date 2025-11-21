from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    health,
    RegisterView,
    LoginView,
    RestaurantViewSet,
    MenuItemViewSet,
    OrderViewSet,
    DeliveryViewSet,
)

router = DefaultRouter()
router.register(r"restaurants", RestaurantViewSet, basename="restaurant")
router.register(r"menu-items", MenuItemViewSet, basename="menuitem")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"deliveries", DeliveryViewSet, basename="delivery")

urlpatterns = [
    path("health/", health, name="Health"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("", include(router.urls)),
]
