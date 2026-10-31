from dashboard.models import UserNotification, WatchlistItem


def check_price_alerts_for_share(share):
    """
    Проверяет целевые ценовые уровни для всех пользователей,
    наблюдающих за акцией share, и формирует уведомления без дублирования.
    """
    if share.last_price is None:
        return

    items = WatchlistItem.objects.filter(share=share).select_related("user")

    for item in items:
        price = share.last_price
        user = item.user

        # Проверка верхнего порога (рост цены)
        if item.target_price_high is not None and price >= item.target_price_high:
            if item.last_notified_type != "HIGH":
                UserNotification.objects.create(
                    user=user,
                    share=share,
                    title=f"🎯 Достигнут верхний целевой уровень {share.ticker}",
                    message=(
                        f"Цена акции {share.name} ({share.ticker}) поднялась до {price} {share.currency}, "
                        f"что выше или равно заданному уровню {item.target_price_high} {share.currency}."
                    ),
                )
                item.last_notified_type = "HIGH"
                item.save(update_fields=["last_notified_type"])

        # Проверка нижнего порога (падение цены)
        elif item.target_price_low is not None and price <= item.target_price_low:
            if item.last_notified_type != "LOW":
                UserNotification.objects.create(
                    user=user,
                    share=share,
                    title=f"⚠️ Цена {share.ticker} опустилась ниже целевого уровня",
                    message=(
                        f"Цена акции {share.name} ({share.ticker}) упала до {price} {share.currency}, "
                        f"что ниже или равно целевому уровню {item.target_price_low} {share.currency}."
                    ),
                )
                item.last_notified_type = "LOW"
                item.save(update_fields=["last_notified_type"])

        # Если цена вернулась в нормальный диапазон между порогами — сбрасываем статус
        elif (
            item.target_price_low is not None
            and item.target_price_high is not None
            and item.target_price_low < price < item.target_price_high
        ):
            if item.last_notified_type is not None:
                item.last_notified_type = None
                item.save(update_fields=["last_notified_type"])
