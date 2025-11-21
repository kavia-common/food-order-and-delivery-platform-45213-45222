from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrStaff(BasePermission):
    """Allows access only to staff or superusers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))


class IsOwnerOrReadOnly(BasePermission):
    """Object-level permission to allow owners to edit; read-only otherwise."""
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        # For orders, customer is the owner
        owner = getattr(obj, "customer", None)
        return bool(user and user.is_authenticated and owner == user)


class CanManageOrderStatus(BasePermission):
    """
    Staff/admin can update any order.
    Customers can only view their own orders.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            # allow customers to view only their own orders
            return obj.customer == request.user or request.user.is_staff or request.user.is_superuser
        # write operations restricted to staff/superuser
        return bool(request.user.is_staff or request.user.is_superuser)


class CanManageDeliveryStatus(BasePermission):
    """
    Staff/admin can update delivery. Couriers assigned to the delivery can update status/location as well.
    Customers can read related to their orders.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in SAFE_METHODS:
            return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or obj.order.customer == user))
        # Write allowed to staff/admin or assigned courier
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or obj.courier == user))
