from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.db import transaction
from django.db.models import Avg, Q
from datetime import datetime, timedelta
from django.http import HttpResponseForbidden
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema

from .models import Product, Offer, User
from .serializers import ProductSerializer, OfferSerializer, UserSerializer
from .services import OffersService


class AuthenticationSchema(AutoSchema):
    global_params = [
        OpenApiParameter(
            name="Access-Token",
            type=str,
            location=OpenApiParameter.HEADER,
            description="Access token from the `auth` endpoint",
        )
    ]

    def get_override_parameters(self):
        params = super().get_override_parameters()
        return params + self.global_params


class OffersServiceMixin:
    offers_service = OffersService()


class AuthenticationMixin:
    schema = AuthenticationSchema()
    
    def dispatch(self, request, *args, **kwargs):
        access_token = request.headers.get('Access-Token')
        try:
            User.objects.get(access_token=access_token)
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            return HttpResponseForbidden('Invalid Access-Token')


class ProductViewSet(AuthenticationMixin, ModelViewSet, OffersServiceMixin):
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
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='includeOffers', type=bool, location=OpenApiParameter.QUERY, description='Return Active Offers for Product'),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        include_offers = request.query_params.get('includeOffers') in [1, 'True', 'true']
        data = serializer.data

        if include_offers:
            offers_data = OfferSerializer(
                instance.offers.filter(items_in_stock__gt=0), many=True
            ).data
            data['offers'] = offers_data

        return Response(data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='fromDay', type=str, location=OpenApiParameter.QUERY, description='Start Date of comparison (DD.MM.YYYY)'),
            OpenApiParameter(name='toDay', type=str, location=OpenApiParameter.QUERY, description='End Date of comparison (DD.MM.YYYY). If none provided Present Day will be used'),
        ],
    )
    @action(detail=True, methods=['get'])
    def price_change(self, request, pk=None):
        product = self.get_object()
        from_day_str = request.query_params.get('fromDay', False)
        if not from_day_str:
            return Response(
                {"error": "You need to provide fromDay parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        to_day_str = request.query_params.get('toDay', False)

        start_day_price = self._calculate_avg_price_for_day(product, from_day_str)
        end_day_price = self._calculate_avg_price_for_day(product, to_day_str)
        
        no_prices_for_days = []
        if not start_day_price:
            no_prices_for_days.append(from_day_str)
        if not end_day_price:
            no_prices_for_days.append(to_day_str if to_day_str else 'Today')
        
        if no_prices_for_days:
            err_msg = f'Couldnt find any Offers for days: {", ".join(no_prices_for_days)}'
            
            return Response(
                {"error": err_msg},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'start_price': start_day_price,
                'end_price': end_day_price,
                'price_change': round((end_day_price / start_day_price - 1) * 100, 2)
            }
        )

    @staticmethod
    def _calculate_avg_price_for_day(product: Product, day_str: str):
        if day_str:
            datetime_bot = datetime.strptime(day_str + ' +0000', '%d.%m.%Y %z')
            datetime_top = datetime_bot + timedelta(days=1)

            q = Q(created_at__lt=datetime_top) & (
                Q(closed_at__gt=datetime_bot) | Q(closed_at__isnull=True)
            )
        else:
            q = Q(closed_at__isnull=True)
        avg_price = product.offers.filter(q).aggregate(avg_price=Avg('price'))[
            'avg_price'
        ]
        try:
            return round(avg_price, 2)
        except:
            return 0


class OfferViewSet(AuthenticationMixin, ReadOnlyModelViewSet, OffersServiceMixin):
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer


class UsersView(APIView):
    serializer_class = UserSerializer
    
    @extend_schema(
        examples=[
            OpenApiExample(
                'Request Access-Token',
                summary='Request Access-Token',
                description='Generates Access-Token for given email.',
                value={
                    'email': 'testUser@gmail.com'
                },
                request_only=True,
            ),
        ]
    )
    def post(self, request, format=None):
        email = request.data.get('email', False)
        if not email:
            return Response(
                {
                    "error": "You need to provide Email address in 'email' Body form data."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance, created = User.objects.get_or_create(email=email)

        serializer = UserSerializer(instance)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)
