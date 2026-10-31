from datetime import timedelta
import logging
from django.utils import timezone
from plotly.graph_objs import Figure, Scatter
from plotly.offline import plot

from dashboard.models import SharePriceHistory
from dashboard.services.alerts import check_price_alerts_for_share
from dashboard.services.strategies import evaluate_strategies_for_share

logger = logging.getLogger("main")


def record_price_and_trigger_events(share, price):
    """
    Сохранение рыночной котировки в историю и запуск связанных проверок:
    1. Запись в SharePriceHistory
    2. Проверка ценовых алертов пользователей (без дублирования)
    3. Проверка и исполнение условий инвестиционных стратегий
    """
    history_entry = SharePriceHistory.objects.create(share=share, price=price)

    # Запуск алертов
    triggered_alerts = check_price_alerts_for_share(share, price)

    # Запуск симулятора стратегий
    executed_strategies = evaluate_strategies_for_share(share, price)

    logger.info(
        f"Зафиксирована цена {share.ticker}: {price}. Сработало алертов: {triggered_alerts}, сделок стратегий: {executed_strategies}"
    )
    return history_entry


record_price_history = record_price_and_trigger_events


def get_price_analytics(share, period="1m"):
    """
    Получение аналитики изменения цен за выбранный период:
    1d, 1w, 1m, 6m, 1y, all.
    Возвращает dict: {records, start_price, end_price, delta_abs, delta_pct}.
    """
    now = timezone.now()
    period_map = {
        "1d": timedelta(days=1),
        "1w": timedelta(days=7),
        "1m": timedelta(days=30),
        "6m": timedelta(days=180),
        "1y": timedelta(days=365),
    }

    qs = SharePriceHistory.objects.filter(share=share)
    if period in period_map:
        qs = qs.filter(recorded_at__gte=now - period_map[period])

    records = list(qs.order_by("recorded_at"))

    if not records:
        base_price = share.last_price or 100.0
        return {
            "records": [],
            "first_price": base_price,
            "last_price": base_price,
            "start_price": base_price,
            "end_price": base_price,
            "min_price": base_price,
            "max_price": base_price,
            "delta": 0.0,
            "delta_abs": 0.0,
            "delta_percent": 0.0,
            "delta_pct": 0.0,
            "trend": "flat",
            "count": 0,
        }

    prices = [r.price for r in records]
    start_price = records[0].price
    end_price = records[-1].price
    min_price = min(prices)
    max_price = max(prices)
    delta_abs = round(end_price - start_price, 2)
    delta_pct = (
        round((delta_abs / start_price) * 100, 2) if start_price != 0 else 0.0
    )
    trend = "up" if delta_abs > 0 else ("down" if delta_abs < 0 else "flat")

    return {
        "records": records,
        "first_price": start_price,
        "last_price": end_price,
        "start_price": start_price,
        "end_price": end_price,
        "min_price": min_price,
        "max_price": max_price,
        "delta": delta_abs,
        "delta_abs": delta_abs,
        "delta_percent": delta_pct,
        "delta_pct": delta_pct,
        "trend": trend,
        "count": len(records),
    }


def build_history_chart(share, period="1m"):
    """Построение интерактивного графика Plotly на основе накопленной истории цен в БД"""
    analytics = get_price_analytics(share, period=period)
    records = analytics["records"]

    if records:
        x_data = [r.recorded_at for r in records]
        y_data = [r.price for r in records]
    else:
        # Если точек в БД пока мало, показываем текущую цену
        now = timezone.now()
        base_price = share.last_price or 100.0
        x_data = [now - timedelta(hours=1), now]
        y_data = [base_price, base_price]

    line_color = "#198754" if analytics["delta_abs"] >= 0 else "#dc3545"

    fig = Figure()
    fig.add_trace(
        Scatter(
            x=x_data,
            y=y_data,
            mode="lines+markers" if len(x_data) <= 30 else "lines",
            name=share.ticker,
            line=dict(color=line_color, width=2),
            marker=dict(size=5),
        )
    )

    period_titles = {
        "1d": "за 1 день",
        "1w": "за 1 неделю",
        "1m": "за 1 месяц",
        "6m": "за 6 месяцев",
        "1y": "за 1 год",
        "all": "за всё время",
    }
    period_title = period_titles.get(period, period)

    fig.update_layout(
        title=dict(
            text=f"История цен {share.name} ({share.ticker}) — {period_title}<br>"
            f"<sub>Динамика: {analytics['delta_abs']:+} {share.currency} ({analytics['delta_pct']:+}%)</sub>",
            x=0.5,
        ),
        xaxis_title="Дата и время",
        yaxis_title=f"Цена ({share.currency})",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
        height=420,
    )

    return plot(
        fig,
        output_type="div",
        include_plotlyjs=False,
    )
