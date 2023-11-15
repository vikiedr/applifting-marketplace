from celery import shared_task
import logging
from datetime import datetime, timezone

from .models import Product, Offer
from .services import OffersService


offers_service = OffersService()
logger = logging.getLogger(__name__)

    
@shared_task
def fetch_offers_task() -> None:
    logging.info(f'Starting Task {fetch_offers_task.__name__}')
    for product in Product.objects.all():
        try:
            available_offers_db = product.offers.filter(items_in_stock__gt=0)
            available_offers_api = offers_service.get_product_offers(product.id)

            is_new_offer = False if available_offers_db.exists() else True
            for offer in available_offers_db:
                matched_offer = next((o for o in available_offers_api if o['id'] == str(offer.id)), None)
                if matched_offer:
                    offer.price = matched_offer['price']
                    offer.items_in_stock = matched_offer['items_in_stock']
                    logging.debug(f'Updated Offer {offer}')
                else:
                    offer.items_in_stock = 0
                    is_new_offer = True
                    offer.closed_at = datetime.now(timezone.utc)
                    logging.debug(f'Offer {offer} Sold Out')
                offer.save()
                    
            if is_new_offer:
                for offer in available_offers_api:
                    if offer['id'] not in (str(o.id) for o in available_offers_db):
                        new_offer = Offer.from_json(offer, product)
                        new_offer.save()
                        logging.debug(f'Saved new Offer {offer}')
        except Exception as e:
            logging.error(f'Unable to get new Offers for Product {product}:\n{e}')
