import httpx
from datetime import datetime, timedelta, timezone
from django.conf import settings
from rest_framework import status
import json

from .models import OfferCredentials

class OffersService:
    def __init__(self) -> None:
        self.base_url = settings.OFFERS_SERVICE_BASE_URL
        refresh_token = settings.OFFERS_SERVICE_REFRESH_TOKEN
        creds, _ = OfferCredentials.objects.get_or_create(
            refresh_token=refresh_token,
            defaults={'refresh_token': refresh_token}
        )
        
        self._credentials = creds
            
    @property
    def access_token(self) -> str:
        time_diff = datetime.now(timezone.utc) - self._credentials.updated_at
        if not self._credentials.access_token or time_diff > timedelta(minutes=5):
            self._get_new_access_token()
        
        return self._credentials.access_token
        
        
    def register_product_for_offers(self, product_data: json) -> None:
        url = f'{self.base_url}/api/v1/products/register'
        headers = {'Bearer': self.access_token}

        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=product_data)

        if response.status_code != status.HTTP_201_CREATED:
            raise Exception(f'Error registering Product with status: {response.status_code}')
    
    def _get_new_access_token(self) -> None:
        url = f'{self.base_url}/api/v1/auth'
        headers = {'Bearer': self._credentials.refresh_token_str}

        with httpx.Client() as client:
            response = client.post(url, headers=headers)
            
        if response.status_code != status.HTTP_201_CREATED:
            raise Exception(f'Error refreshing Access Token with status: {response.status_code}')
        
        self._credentials.access_token = response.json()['access_token']
        self._credentials.save()
