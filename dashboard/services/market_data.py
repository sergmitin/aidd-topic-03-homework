import logging
from config.settings import TINKOFF_TOKEN

logger = logging.getLogger("main")


def get_last_data(share):
    """
    Получение актуальной рыночной цены акции с учетом копеек/центов (nano).
    Если токен не задан или внешнее API недоступно, возвращается None без падения системы.
    """
    if not TINKOFF_TOKEN:
        logger.warning(
            f"TINKOFF_TOKEN не настроен. Пропуск внешнего запроса котировки для {share.ticker}."
        )
        return None

    try:
        from tinkoff.invest import Client
    except ImportError:
        logger.warning(
            "Пакет tinkoff-investments не установлен. Пропуск внешнего запроса."
        )
        return None

    try:
        with Client(TINKOFF_TOKEN) as client:
            resp = client.market_data.get_last_prices(figi=[share.figi])
            if not resp.last_prices:
                logger.warning(f"Пустой ответ цен от API для инструмента {share.figi}")
                return None

            last_price_obj = resp.last_prices[0]
            # Точный расчет цены: целая часть + дробная нано-часть (1 nano = 1e-9)
            raw_units = getattr(last_price_obj.price, "units", 0)
            raw_nano = getattr(last_price_obj.price, "nano", 0)
            exact_price = round(float(raw_units) + (float(raw_nano) / 1_000_000_000), 2)
            timestamp = getattr(last_price_obj, "time", None)

            logger.info(
                f"Получена котировка для {share.ticker} ({share.id}): {exact_price} {share.currency}"
            )
            return [exact_price, timestamp]
    except Exception as e:
        logger.error(f"Ошибка запроса котировок Tinkoff API для {share.ticker}: {e}")
        return None
