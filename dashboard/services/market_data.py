import logging

from config.settings import TINKOFF_TOKEN
from dashboard.services.price_utils import quotation_to_float

logger = logging.getLogger("main")


def get_last_price(share):
    """
    Возвращает последнюю рыночную цену акции.
    Если TINKOFF_TOKEN задан и библиотека tinkoff доступна — запрашивает API.
    Иначе возвращает текущую цену инструмента (или fallback).
    """
    if TINKOFF_TOKEN:
        try:
            from tinkoff.invest import Client

            with Client(TINKOFF_TOKEN) as client:
                resp = client.market_data.get_last_prices(figi=[share.figi])
                quotation = resp.last_prices.pop().price
                logger.info(f"Get last data for share with id {share.id}")
                return quotation_to_float(quotation)
        except Exception as e:
            logger.error(f"Error fetching Tinkoff price for {share.ticker}: {e}")

    # Fallback режим: возвращаем текущую цену акции или 0.0
    return share.last_price if share.last_price is not None else 0.0
