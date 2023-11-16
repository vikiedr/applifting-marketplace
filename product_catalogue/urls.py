from django.urls import path, include
from rest_framework.routers import DefaultRouter
from product_catalogue import views

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename="product")
router.register(r'offers', views.OfferViewSet, basename="offer")

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api/v1/auth', views.UsersView.as_view(), name='auth'),
    path('api/docs/schema', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
