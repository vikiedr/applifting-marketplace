from rest_framework.test import APIClient
from rest_framework import status
import pytest
from django.urls import reverse
from unittest.mock import patch

from product_catalogue.tasks import fetch_offers_task
from product_catalogue.models import Product, Offer
from product_catalogue.serializers import OfferSerializer


@patch("product_catalogue.services.OffersService")
@pytest.mark.django_db
def test_create_product(mock_register_product_for_offers):
    client = APIClient()
    url = reverse('product-list')
    data = {'name': 'Test Product', 'description': 'Test Description'}
    mock_register_product_for_offers.return_value = None
    
    response = client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

    assert Product.objects.count() == 1
    product = Product.objects.first()
    assert product.name == 'Test Product'
    assert product.description == 'Test Description'
    
@pytest.mark.django_db
def test_create_product_error():
    with patch('product_catalogue.services.OffersService.register_product_for_offers', side_effect=Exception()):
        client = APIClient()
        url = reverse('product-list')
        data = {'name': 'Test Product', 'description': 'Test Description'}
        
        response = client.post(url, data, format='json')
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        assert Product.objects.count() == 0

@pytest.mark.django_db
def test_retrieve_product_without_offers():
    product = _create_test_product()
    client = APIClient()
    url = reverse('product-detail', args=[product.id])

    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Test Product'
    assert response.data['description'] == 'Test Description'
    assert 'offers' not in response.data

@pytest.mark.django_db
def test_retrieve_product_with_offers():
    offer_count = 5
    product = _create_test_product()
    _create_test_offers(product, offer_count)
    client = APIClient()
    url = reverse('product-detail', args=[product.id])

    response = client.get(f"{url}?includeOffers=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Test Product'
    assert response.data['description'] == 'Test Description'
    assert len(response.data.get('offers', [])) == offer_count - 1

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

@pytest.mark.django_db
def test_retrieve_offer():
    product = _create_test_product()
    offer = _create_test_offers(product, 1)[0]
    client = APIClient()
    url = reverse('offer-detail', args=[offer.id])

    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['price'] == 500
    assert response.data['items_in_stock'] == 0
    assert response.data['product'] == product.id

@pytest.mark.django_db
def test_list_offers():
    offer_count = 5
    product = _create_test_product()
    _create_test_offers(product, offer_count)
    client = APIClient()
    url = reverse('offer-list')

    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == offer_count
    
@patch('product_catalogue.tasks.offers_service.get_product_offers')
@pytest.mark.django_db
def test_list_offers(mock_get_product_offers):
    product = _create_test_product()
    offers = _create_test_offers(product)
    
    offers = offers[2:]
    offers.append(
        Offer(
            price=10000,
            items_in_stock=200,
            product=product,
        )
    )
    serializer = OfferSerializer(offers, many=True)
    offers_from_api = serializer.data
    offers_from_api[0]['price'] += 20
    mock_get_product_offers.return_value = offers_from_api

    fetch_offers_task()
    new_offers = Offer.objects.all()
    assert new_offers.count() == 6
    assert new_offers.filter(items_in_stock__gt=0).count() == 4
    assert new_offers.filter(price=10000).count() == 1
    

def _create_test_product() -> Product:
    product = Product.objects.create(name='Test Product', description='Test Description')
    return product

def _create_test_offers(product: Product, count: int=5) -> [Offer]:
    """
    Creates 'count' Offers where 1 Offer is Sold Out
    """
    return [
        Offer.objects.create(
            price=(i + 1) * 500,
            items_in_stock=i * 30,
            product=product,
        )
        for i in range(count)
    ]