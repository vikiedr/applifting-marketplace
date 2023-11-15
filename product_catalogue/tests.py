from rest_framework.test import APIClient
from rest_framework import status
import pytest
from django.urls import reverse
from unittest.mock import patch
from datetime import datetime, timedelta
from uuid import uuid4

from product_catalogue.tasks import fetch_offers_task
from product_catalogue.models import Product, Offer, User
from product_catalogue.serializers import OfferSerializer


@pytest.fixture
@pytest.mark.django_db
def user():
    user = User.objects.create(email='testuser@gmail.com', access_token=uuid4())
    return user


@patch("product_catalogue.services.OffersService")
@pytest.mark.django_db
def test_create_product(mock_register_product_for_offers, user):
    url = reverse('product-list')
    data = {'name': 'Test Product', 'description': 'Test Description'}
    mock_register_product_for_offers.return_value = None

    response = _send_post_request_auth(url, data, user)
    assert response.status_code == status.HTTP_201_CREATED

    assert Product.objects.count() == 1
    product = Product.objects.first()
    assert product.name == 'Test Product'
    assert product.description == 'Test Description'


@pytest.mark.django_db
def test_create_product_error(user):
    with patch(
        'product_catalogue.services.OffersService.register_product_for_offers',
        side_effect=Exception(),
    ):
        url = reverse('product-list')
        data = {'name': 'Test Product', 'description': 'Test Description'}

        response = _send_post_request_auth(url, data, user)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert Product.objects.count() == 0


@pytest.mark.django_db
def test_retrieve_product_without_offers(user):
    product = _create_test_product()
    url = reverse('product-detail', args=[product.id])

    response = _send_get_request_auth(url, user)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Test Product'
    assert response.data['description'] == 'Test Description'
    assert 'offers' not in response.data


@pytest.mark.django_db
def test_retrieve_product_with_offers(user):
    offer_count = 5
    product = _create_test_product()
    _create_test_offers(product, offer_count)
    url = reverse('product-detail', args=[product.id])

    response = _send_get_request_auth(f"{url}?includeOffers=1", user)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Test Product'
    assert response.data['description'] == 'Test Description'
    assert len(response.data.get('offers', [])) == offer_count - 1


@pytest.mark.django_db
def test_list_product(user):
    [_create_test_product() for _ in range(4)]
    url = reverse('product-list')

    response = _send_get_request_auth(url, user)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 4


@pytest.mark.django_db
def test_update_product(user):
    product = _create_test_product()
    client = APIClient()
    url = reverse('product-detail', args=[product.id])
    data = {'name': 'Updated Product', 'description': 'Updated Description'}

    headers = _get_access_token_header(user)
    response = client.put(url, data, format='json', headers=headers)
    assert response.status_code == status.HTTP_200_OK

    product.refresh_from_db()
    assert product.name == 'Updated Product'
    assert product.description == 'Updated Description'


@pytest.mark.django_db
def test_delete_product(user):
    product = _create_test_product()
    client = APIClient()
    url = reverse('product-detail', args=[product.id])

    headers = _get_access_token_header(user)
    response = client.delete(url, headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert Product.objects.count() == 0


@pytest.mark.django_db
def test_retrieve_offer(user):
    product = _create_test_product()
    offer = _create_test_offers(product, 1)[0]
    url = reverse('offer-detail', args=[offer.id])

    response = _send_get_request_auth(url, user)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['price'] == 500
    assert response.data['items_in_stock'] == 0
    assert response.data['product'] == product.id


@pytest.mark.django_db
def test_list_offers(user):
    offer_count = 5
    product = _create_test_product()
    _create_test_offers(product, offer_count)
    url = reverse('offer-list')

    response = _send_get_request_auth(url, user)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == offer_count


@patch('product_catalogue.tasks.offers_service.get_product_offers')
@pytest.mark.django_db
def test_fetch_offers_task(mock_get_product_offers):
    product = _create_test_product()
    offers = _create_test_offers(product)

    offers_from_api = offers[2:]
    offers_from_api.append(
        Offer(
            price=10000,
            items_in_stock=200,
            product=product,
        )
    )
    serializer = OfferSerializer(offers_from_api, many=True)
    offers_from_api = serializer.data
    offers_from_api[0]['price'] += 20
    mock_get_product_offers.return_value = offers_from_api

    fetch_offers_task()
    new_offers = Offer.objects.all()
    assert new_offers.count() == 6
    assert new_offers.filter(items_in_stock__gt=0).count() == 4
    assert new_offers.filter(price=10000).count() == 1
    assert new_offers.get(id=offers[1].id).closed_at is not None


@pytest.mark.django_db
def test_product_offers_compare_two_dates(user):
    product = _create_test_product()
    from_day = "10.04.2020"
    to_day = "23.06.2021"
    url = (
        f'/api/v1/products/{product.id}/price_change/?fromDay={from_day}&toDay={to_day}'
    )
    _create_offers_for_compare_tests(product, from_day, to_day)

    response = _send_get_request_auth(url, user)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['start_price'] == 1250
    assert response.data['end_price'] == 3833.33


@pytest.mark.django_db
def test_product_offers_compare_only_with_start_day(user):
    product = _create_test_product()
    from_day = "10.04.2020"
    to_day = "23.06.2021"
    url = f'/api/v1/products/{product.id}/price_change/?fromDay={from_day}'
    _create_offers_for_compare_tests(product, from_day, to_day)

    response = _send_get_request_auth(url, user)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['start_price'] == 1250
    assert response.data['end_price'] == 5000


@pytest.mark.django_db
def test_product_offers_compare_without_fromDay_parameter(user):
    product = _create_test_product()
    url = f'/api/v1/products/{product.id}/price_change/'

    response = _send_get_request_auth(url, user)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_user_creation(user):
    client = APIClient()
    url = reverse('auth')
    data = {'email': 'test@gmail.com'}
    response = client.post(url, data, format='json')

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_user_creation_missing_email(user):
    client = APIClient()
    url = reverse('auth')
    data = {}
    response = client.post(url, data, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_list_products_no_auth():
    client = APIClient()
    url = reverse('product-list')

    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_offers_no_auth():
    client = APIClient()
    url = reverse('offer-list')

    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def _create_offers_for_compare_tests(
    product: Product, from_day: str, to_day: str
) -> None:
    from_day = datetime.strptime(from_day, '%d.%m.%Y')
    to_day = datetime.strptime(to_day, '%d.%m.%Y')
    _create_closed_offer(product, from_day - timedelta(hours=10), 500)
    _create_closed_offer(product, from_day - timedelta(hours=3), 1000)
    _create_closed_offer(product, from_day + timedelta(hours=3), 1500)
    _create_closed_offer(product, from_day + timedelta(hours=25), 2000)
    _create_closed_offer(product, to_day - timedelta(hours=10), 2500)
    _create_closed_offer(product, to_day - timedelta(hours=3), 3000)
    _create_closed_offer(product, to_day + timedelta(hours=3), 3500)
    _create_closed_offer(product, to_day + timedelta(hours=25), 4000)

    Offer.objects.create(
        price=5000,
        items_in_stock=20,
        product=product,
        created_at=to_day + timedelta(hours=20),
    )


def _create_test_product() -> Product:
    product = Product.objects.create(
        name='Test Product', description='Test Description'
    )
    return product


def _create_test_offers(product: Product, count: int = 5) -> [Offer]:
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


def _create_closed_offer(product: Product, created_at: datetime, price: int) -> Offer:
    return Offer.objects.create(
        price=price,
        items_in_stock=0,
        product=product,
        created_at=created_at,
        closed_at=created_at + timedelta(hours=5),
    )


def _send_get_request_auth(url: str, user: User):
    headers = _get_access_token_header(user)
    client = APIClient()
    return client.get(url, headers=headers)


def _send_post_request_auth(url: str, data: dict, user: User):
    headers = _get_access_token_header(user)
    client = APIClient()
    return client.post(url, data, format='json', headers=headers)


def _get_access_token_header(user: User):
    return {'Access-Token': user.access_token}
