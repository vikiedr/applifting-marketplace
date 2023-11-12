from rest_framework.test import APIClient
from rest_framework import status
import pytest
from django.urls import reverse
from .models import Product

@pytest.mark.django_db
def test_create_product():
    client = APIClient()
    url = reverse('product-list')
    data = {'name': 'Test Product', 'description': 'Test Description'}
    
    response = client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

    assert Product.objects.count() == 1
    product = Product.objects.first()
    assert product.name == 'Test Product'
    assert product.description == 'Test Description'

@pytest.mark.django_db
def test_retrieve_product():
    product = _create_test_product()
    client = APIClient()
    url = reverse('product-detail', args=[product.id])

    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Test Product'
    assert response.data['description'] == 'Test Description'

@pytest.mark.django_db
def test_list_product():
    [_create_test_product() for _ in range(4)]
    client = APIClient()
    url = reverse('product-list')

    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 4

@pytest.mark.django_db
def test_update_product():
    product = _create_test_product()
    client = APIClient()
    url = reverse('product-detail', args=[product.id])
    data = {'name': 'Updated Product', 'description': 'Updated Description'}

    response = client.put(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK

    product.refresh_from_db()
    assert product.name == 'Updated Product'
    assert product.description == 'Updated Description'

@pytest.mark.django_db
def test_delete_product():
    product = _create_test_product()
    client = APIClient()
    url = reverse('product-detail', args=[product.id])

    response = client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert Product.objects.count() == 0

def _create_test_product() -> Product:
    product = Product.objects.create(name='Test Product', description='Test Description')
    return product
