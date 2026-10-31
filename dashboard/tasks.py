import logging
import random

from config.celery import app
from config.settings import TINKOFF_TOKEN
from dashboard.models import Share
from dashboard.services.alerts import check_price_alerts_for_share
from dashboard.services.market_data import get_last_price
from dashboard.services.price_history import record_price_change
from dashboard.services.price_utils import calculate_trend
from dashboard.services.strategies import evaluate_strategies_for_share

logger = logging.getLogger("main")


def process_share_price_update(share, new_price, source="market"):
    """
    Применяет новую цену акции:
    - Обновляет тренд и цену в БД
    - Сохраняет точку в историю цен
    - Проверяет персональные алерты пользователей
    - Запускает симулятор торговых стратегий
    """
    if new_price is None or new_price <= 0:
        return

    is_trend_high = calculate_trend(share.last_price, new_price)
    share.last_price = round(new_price, 2)
    share.is_trend_high = is_trend_high
    share.save(update_fields=["last_price", "is_trend_high", "updated_at"])

    # Запись в историю цен
    record_price_change(share, share.last_price, source=source)

    # Проверка целевых уровней (алерты)
    check_price_alerts_for_share(share)

    # Запуск автостратегий
    evaluate_strategies_for_share(share)


@app.task
def update_last_price():
    """
    Периодическая задача обновления цен.
    Если TINKOFF_TOKEN задан — запрашивает внешнее API.
    Если нет — выполняет реалистичную микро-симуляцию рыночных торгов (±0.5%–1.5%).
    """
    shares = Share.objects.all()

    for share in shares:
        try:
            if TINKOFF_TOKEN:
                last_price = get_last_price(share)
                source = "tinkoff"
            else:
                # Симуляция рыночных колебаний в демо-режиме
                current = share.last_price if share.last_price else 100.0
                delta_percent = random.uniform(-0.02, 0.02)
                last_price = round(current * (1 + delta_percent), 2)
                source = "simulator"

            process_share_price_update(share, last_price, source=source)
        except Exception as e:
            logger.error(f"Error updating price for share {share.ticker}: {e}")
