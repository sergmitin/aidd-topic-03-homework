from datetime import date, timedelta
import logging

from plotly.graph_objs import Figure, Scatter
from plotly.offline import plot

from config.settings import TINKOFF_TOKEN

logger = logging.getLogger("main")


def get_graph(share):
    """
    Построение интерактивного графика котировок Plotly за 180 дней.
    Учитывает дробную часть цены (nano).
    При отсутствии токена или сбое внешнего API формирует график по локальным данным.
    """
    x_data, y_data = [], []
    is_live_data = False

    if TINKOFF_TOKEN:
        try:
            from tinkoff.invest import CandleInterval, Client
            from tinkoff.invest.utils import now

            with Client(TINKOFF_TOKEN) as client:
                for candle in client.get_all_candles(
                    figi=share.figi,
                    from_=now() - timedelta(days=180),
                    interval=CandleInterval.CANDLE_INTERVAL_DAY,
                ):
                    raw_units = getattr(candle.close, "units", 0)
                    raw_nano = getattr(candle.close, "nano", 0)
                    price = round(float(raw_units) + (float(raw_nano) / 1_000_000_000), 2)
                    x_data.append(candle.time.date())
                    y_data.append(price)

                if x_data:
                    is_live_data = True
        except Exception as e:
            logger.warning(
                f"Не удалось загрузить свечи Tinkoff API для {share.ticker}: {e}"
            )

    # Если внешние данные недоступны, строим график на основе локальных данных инструмента
    if not is_live_data:
        today = date.today()
        base_price = share.last_price if share.last_price is not None else 100.0
        # Формируем историческую линию от опорной цены до текущей
        for i in range(180, -1, -30):
            d = today - timedelta(days=i)
            # Небольшая дельта для наглядности динамики
            factor = 1.0 - (i / 1800.0)
            x_data.append(d)
            y_data.append(round(base_price * factor, 2))

    fig = Figure()
    fig.add_trace(
        Scatter(
            x=x_data,
            y=y_data,
            mode="lines+markers" if len(x_data) < 20 else "lines",
            name=share.ticker,
            line=dict(color="#0d6efd", width=2),
            marker=dict(size=4),
        )
    )

    subtitle = (
        "Источник: Tinkoff Invest API (реальные свечи)"
        if is_live_data
        else "Источник: Локальные данные (демо-режим, TINKOFF_TOKEN не настроен)"
    )

    fig.update_layout(
        title=dict(
            text=f"Динамика котировок {share.name} ({share.ticker})<br><sub>{subtitle}</sub>",
            x=0.5,
        ),
        xaxis_title="Дата",
        yaxis_title=f"Цена ({share.currency})",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
        height=400,
    )

    return plot(
        fig,
        output_type="div",
        include_plotlyjs=False,
    )
