from django.urls import path, include
from rest_framework.routers import DefaultRouter
from product_catalogue import views


router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename="product")
router.register(r'offers', views.OfferViewSet, basename="offer")

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api/v1/auth', views.UsersView.as_view(), name='auth'),
]
