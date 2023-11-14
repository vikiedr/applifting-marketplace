from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from .models import Product, Offer
from .serializers import ProductSerializer, OfferSerializer
from .services import OffersService


class OffersServiceMixin:
    offers_service = OffersService()


class ProductViewSet(ModelViewSet, OffersServiceMixin):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            self.perform_create(serializer)
            
            try:
                self.offers_service.register_product_for_offers(serializer.data)
            except:
                transaction.set_rollback(True)
                
                return Response(
                    {"error": f"Failed to perform register Products for Offers."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        include_offers = request.query_params.get('includeOffers', False)
        data = serializer.data
        
        if include_offers:
            offers_data = OfferSerializer(instance.offers.filter(items_in_stock__gt=0), many=True).data
            data['offers'] = offers_data

        return Response(data)

class OfferViewSet(ReadOnlyModelViewSet, OffersServiceMixin):
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
