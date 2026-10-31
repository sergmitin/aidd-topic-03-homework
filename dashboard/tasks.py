import logging
from django.utils import timezone

from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data

logger = logging.getLogger("main")


@app.task
def update_last_price():
    """Фоновое обновление котировок акций"""
    shares = Share.objects.all()

    for share in shares:
        try:
            data = get_last_data(share)
            if not data:
                continue

            last_price, _ = data

            if share.last_price is not None:
                is_trend_high = bool(last_price >= share.last_price)
            else:
                is_trend_high = True

            Share.objects.filter(id=share.id).update(
                last_price=last_price,
                is_trend_high=is_trend_high,
                updated_at=timezone.now(),
            )
            logger.info(
                f"Успешно обновлена цена {share.ticker}: {last_price} (рост: {is_trend_high})"
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении котировки акции {share.ticker}: {e}")
