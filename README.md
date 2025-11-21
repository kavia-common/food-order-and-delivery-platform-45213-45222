# food-order-and-delivery-platform-45213-45222

Backend: Django + Django REST Framework

- API docs: /docs (Swagger UI) and /redoc when server is running.
- Base path: /api/

Core Endpoints
- GET /api/health/ -> {"message": "Server is up!"}
- POST /api/auth/register/ -> create user {username, email, password}
- POST /api/auth/login/ -> session login {username, password}

Restaurants and Menus
- GET /api/restaurants/?q=... -> list restaurants (paginated)
- GET /api/restaurants/{id}/ -> restaurant details
- GET /api/restaurants/{id}/menu/ -> menu for restaurant (paginated)
- GET /api/menu-items/?restaurant_id=... -> list menu items (paginated)
- GET /api/menu-items/{id}/ -> menu item details

Orders
- GET /api/orders/ -> list your orders (staff sees all)
- POST /api/orders/ -> create order:
  {
    "restaurant_id": 1,
    "delivery_address": "123 Main St",
    "notes": "",
    "items": [
      {"menu_item_id": 10, "quantity": 2},
      {"menu_item_id": 11, "quantity": 1}
    ]
  }
- GET /api/orders/{id}/ -> order detail (includes items and delivery)
- GET /api/orders/{id}/status/ -> current order status
- PATCH /api/orders/{id}/status/ -> update status (staff/admin only), body: {"status": "preparing"}

Deliveries
- GET /api/deliveries/ -> staff/admin see all, courier sees assigned, customer sees own
- GET /api/deliveries/{id}/ -> delivery details
- GET /api/deliveries/{id}/status/ -> delivery status
- PATCH /api/deliveries/{id}/ -> update fields (status/eta/current_location); allowed for staff/admin or assigned courier

Permissions
- Customers can create and view their orders and related delivery.
- Staff/Admin can update order and delivery statuses.
- Couriers (regular users) can update deliveries assigned to them.

Notes
- Uses session authentication for simplicity in this template. For production, switch to token/JWT auth.
- Pagination supported via page and page_size query params.
