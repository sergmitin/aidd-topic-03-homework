import logging
from django.utils import timezone

from dashboard.models import PriceAlert, Share, UserNotification, WatchlistItem

logger = logging.getLogger("main")


def toggle_watchlist(user, share_id):
    """
    Добавление или удаление акции из списка наблюдения (Watchlist).
    Возвращает (is_added: bool, share: Share).
    """
    share = Share.objects.get(id=share_id)
    item, created = WatchlistItem.objects.get_or_create(user=user, share=share)
    if not created:
        item.delete()
        return False, share
    return True, share


def create_price_alert(user, share_id, target_price, condition="above"):
    """Создание целевого ценового уровня для акции"""
    share = Share.objects.get(id=share_id)
    alert = PriceAlert.objects.create(
        user=user,
        share=share,
        target_price=float(target_price),
        condition=condition,
        is_active=True,
        is_triggered=False,
    )
    return alert


def check_price_alerts_for_share(share, current_price):
    """
    Автоматическая проверка ценовых алертов по акции.
    Исключает дублирование: сработавший алерт переводится в is_triggered=True.
    """
    active_alerts = PriceAlert.objects.filter(
        share=share, is_active=True, is_triggered=False
    )
    triggered_count = 0

    for alert in active_alerts:
        condition_met = False
        if alert.condition == "above" and current_price >= alert.target_price:
            condition_met = True
            cond_text = "поднялась выше целевого уровня"
        elif alert.condition == "below" and current_price <= alert.target_price:
            condition_met = True
            cond_text = "опустилась ниже целевого уровня"

        if condition_met:
            # Отмечаем алерт как сработавший (исключая дубликат при следующем тике)
            alert.is_triggered = True
            alert.triggered_at = timezone.now()
            alert.save()

            title = f"Ценовой уровень {share.ticker}: {alert.target_price} {share.currency}"
            message = (
                f"Цена акции {share.name} ({share.ticker}) {cond_text} {alert.target_price} {share.currency} "
                f"и составляет сейчас {current_price} {share.currency}."
            )
            UserNotification.objects.create(
                user=alert.user,
                title=title,
                message=message,
            )
            triggered_count += 1
            logger.info(f"Сработал ценовой алерт ID {alert.id} для пользователя {alert.user.email}")

    return triggered_count


check_and_trigger_alerts = check_price_alerts_for_share
