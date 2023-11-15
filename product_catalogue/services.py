import httpx
from datetime import datetime, timedelta, timezone
from django.conf import settings
from rest_framework import status
import json
import logging

from .models import OfferCredentials


logger = logging.getLogger(__name__)


class OffersService:
    _credentials = None

    def refresh_token_on_failure(func):
        def wrap(*args, **kwargs):
            args[0]._set_credentials()
            try:
                return func(*args, **kwargs)
            except PermissionError:
                logger.info('Invalid Access Token. Refreshing...')
                args[0]._generate_new_access_token()
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f'Encountered Error during {func.__name__}:\n{e}')
                raise

        return wrap

    @refresh_token_on_failure
    def register_product_for_offers(self, product_data: json) -> None:
        url = f'{self.base_url}/api/v1/products/register'
        headers = {'Bearer': self._credentials.access_token}

        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=product_data)

        err_msg = f'Error registering Product with status: {response.status_code}'
        self._handle_response_status(
            response.status_code, status.HTTP_201_CREATED, err_msg
        )

    @refresh_token_on_failure
    def get_product_offers(self, product_id: str) -> [json]:
        url = f'{self.base_url}/api/v1/products/{product_id}/offers'
        headers = {'Bearer': self._credentials.access_token}

        with httpx.Client() as client:
            response = client.get(url, headers=headers)

        err_msg = f'Error fetching Offers for Product {product_id} with status: {response.status_code}'
        self._handle_response_status(response.status_code, status.HTTP_200_OK, err_msg)

        return response.json()

    def _generate_new_access_token(self) -> None:
        self._set_credentials()

        time_diff = datetime.now(timezone.utc) - self._credentials.updated_at
        if self._credentials.access_token and time_diff < timedelta(minutes=5):
            logger.info('Access Token appears to be still Valid!')
            return

        url = f'{self.base_url}/api/v1/auth'
        headers = {'Bearer': self._credentials.refresh_token_str}

        with httpx.Client() as client:
            response = client.post(url, headers=headers)

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            return
        if response.status_code != status.HTTP_201_CREATED:
            raise Exception(
                f'Error refreshing Access Token with status: {response.status_code}'
            )

        self._credentials.access_token = response.json()['access_token']
        self._credentials.save()
        logger.info('Refreshed Access Token and saved to DB')

    def _set_credentials(self) -> None:
        if not self._credentials:
            self.base_url = settings.OFFERS_SERVICE_BASE_URL
            refresh_token = settings.OFFERS_SERVICE_REFRESH_TOKEN
            creds, _ = OfferCredentials.objects.get_or_create(
                refresh_token=refresh_token, defaults={'refresh_token': refresh_token}
            )
            self._credentials = creds
        else:
            self._credentials = OfferCredentials.objects.get(
                refresh_token=self._credentials.refresh_token
            )

    @staticmethod
    def _handle_response_status(
        status_code: int, acceptable_status_code: status, error_message: str
    ) -> None:
        if status_code == status.HTTP_401_UNAUTHORIZED:
            raise PermissionError("Access Token invalid")
        if status_code != acceptable_status_code:
            raise Exception(error_message)
