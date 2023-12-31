from rest_framework.serializers import ModelSerializer

from .models import Product, Offer, User


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description']


class OfferSerializer(ModelSerializer):
    class Meta:
        model = Offer
        fields = ['id', 'price', 'items_in_stock', 'product']


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'access_token']
