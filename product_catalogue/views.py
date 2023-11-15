from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.db import transaction
from django.db.models import Avg, Q
from datetime import datetime, timedelta

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
    
    @action(detail=True, methods=['get'])
    def price_change(self, request, pk=None):
        product = self.get_object()
        from_day_str = request.query_params.get('fromDay', False)
        if not from_day_str:
                return Response(
                    {"error": "You need to provide fromDay parameter."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        to_day_str = request.query_params.get('toDay', False)

        start_day_price = self._calculate_avg_price_for_day(product, from_day_str)
        end_day_price = self._calculate_avg_price_for_day(product, to_day_str)
    
        return Response({
            'start_price': start_day_price,
            'end_price': end_day_price,
        })

    @staticmethod
    def _calculate_avg_price_for_day(product: Product, day_str: str):
        if day_str:
            datetime_bot = datetime.strptime(day_str, '%d.%m.%Y')
            datetime_top = datetime_bot + timedelta(days=1)
        
            q = Q(created_at__lt=datetime_top) & (Q(closed_at__gt=datetime_bot) | Q(closed_at__isnull=True))
        else:
            q = Q(closed_at__isnull=True)
        avg_price = product.offers.filter(q).aggregate(avg_price=Avg('price'))['avg_price']
        return round(avg_price, 2)
    
    
class OfferViewSet(ReadOnlyModelViewSet, OffersServiceMixin):
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
