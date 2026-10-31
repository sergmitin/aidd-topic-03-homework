import logging

from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_price
from dashboard.services.price_utils import calculate_trend

logger = logging.getLogger("main")


@app.task
def update_last_price():
    shares = Share.objects.all()

    for share in shares:
        try:
            last_price = get_last_price(share)
            is_trend_high = calculate_trend(share.last_price, last_price)

            share.last_price = last_price
            share.is_trend_high = is_trend_high
            # Используем .save() вместо .update() чтобы auto_now корректно
            # обновил поле updated_at
            share.save(update_fields=["last_price", "is_trend_high", "updated_at"])
        except Exception as e:
            logger.error(e)
