from django.db import models
from django.utils import timezone
import uuid


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return f'{self.name} ({self.id})'


class Offer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price = models.IntegerField()
    items_in_stock = models.IntegerField()
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='offers'
    )
    created_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(default=None, null=True)

    @classmethod
    def from_json(cls, json_data, product):
        return cls(
            id=json_data.get('id'),
            price=json_data.get('price'),
            items_in_stock=json_data.get('items_in_stock'),
            product=product,
        )

    def __str__(self):
        return f'{self.product.name}: {self.price} ({self.items_in_stock} left)'


class OfferCredentials(models.Model):
    refresh_token = models.UUIDField(primary_key=True, editable=False)
    access_token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def refresh_token_str(self):
        return str(self.refresh_token) if self.refresh_token else None


class User(models.Model):
    email = models.EmailField(primary_key=True, editable=False)
    access_token = models.UUIDField(default=uuid.uuid4, editable=False)
