from django.urls import path, include
from rest_framework.routers import DefaultRouter
from product_catalogue import views


router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename="product")

urlpatterns = [
    path('api/v1/', include(router.urls)),
]