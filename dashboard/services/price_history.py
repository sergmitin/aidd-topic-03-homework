from datetime import timedelta
from django.utils import timezone
from plotly.graph_objs import Figure, Scatter
from plotly.offline import plot

from dashboard.models import PriceHistory


def record_price_change(share, price, source="market"):
    """
    Записывает цену акции в историю, если она изменилась или это первая запись.
    """
    if price is None:
        return None

    last_record = PriceHistory.objects.filter(share=share).order_by("-created_at").first()
    if last_record and abs(last_record.price - price) < 1e-6:
        # Цена не изменилась, не спамим дубликатами
        return last_record

    return PriceHistory.objects.create(share=share, price=price, source=source)


def get_price_statistics(share, days=30):
    """
    Рассчитывает абсолютное и процентное изменение стоимости за выбранный период.
    """
    since_date = timezone.now() - timedelta(days=days)
    history = (
        PriceHistory.objects.filter(share=share, created_at__gte=since_date)
        .order_by("created_at")
    )

    if not history.exists():
        # Если записей за период нет, берем все существующие
        history = PriceHistory.objects.filter(share=share).order_by("created_at")

    if not history.exists():
        current_p = share.last_price or 0.0
        return {
            "start_price": current_p,
            "current_price": current_p,
            "abs_change": 0.0,
            "percent_change": 0.0,
            "min_price": current_p,
            "max_price": current_p,
            "points_count": 0,
        }

    first_entry = history.first()
    start_price = first_entry.price
    current_price = share.last_price if share.last_price is not None else history.last().price

    abs_change = round(current_price - start_price, 2)
    percent_change = (
        round((abs_change / start_price) * 100, 2) if start_price > 0 else 0.0
    )

    all_prices = [h.price for h in history]
    return {
        "start_price": start_price,
        "current_price": current_price,
        "abs_change": abs_change,
        "percent_change": percent_change,
        "min_price": min(all_prices),
        "max_price": max(all_prices),
        "points_count": len(all_prices),
    }


def build_history_chart(share):
    """
    Строит график динамики рыночной цены на основе накопленной истории из базы данных.
    """
    records = PriceHistory.objects.filter(share=share).order_by("created_at")
    if not records.exists():
        if share.last_price:
            # Создаем начальную точку
            record_price_change(share, share.last_price, source="initial")
            records = PriceHistory.objects.filter(share=share).order_by("created_at")

    x_vals = [r.created_at for r in records]
    y_vals = [r.price for r in records]

    fig = Figure()
    fig.add_trace(
        Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines+markers",
            name=f"{share.ticker} (История БД)",
            line=dict(color="#198754", width=3),
            marker=dict(size=6, color="#0f5132"),
        )
    )

    fig.update_layout(
        title=dict(
            text=f"История изменения рыночных цен: {share.name} ({share.ticker})",
            x=0.5,
        ),
        xaxis_title="Дата и время фиксации",
        yaxis_title=f"Цена ({share.currency})",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
        height=380,
    )

    return plot(fig, output_type="div", include_plotlyjs=True)
