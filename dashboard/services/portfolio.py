from django.db import transaction
from django.utils import timezone

from dashboard.models import Portfolio, PortfolioPosition, PortfolioTransaction, Share


def get_or_create_portfolio(user):
    """Получение или создание основного портфеля пользователя"""
    portfolio, _ = Portfolio.objects.get_or_create(
        user=user, defaults={"name": "Основной портфель", "cash_balance": 100000.0}
    )
    return portfolio


@transaction.atomic
def buy_share(user, share_id, quantity):
    """
    Покупка акций в виртуальный портфель.
    Возвращает (успех: bool, сообщение: str).
    """
    if quantity <= 0:
        return False, "Количество акций должно быть больше нуля."

    portfolio = get_or_create_portfolio(user)
    try:
        share = Share.objects.get(id=share_id)
    except Share.DoesNotExist:
        return False, "Указанная акция не найдена."

    price = share.last_price or 100.0
    total_cost = round(price * quantity, 2)

    if portfolio.cash_balance < total_cost:
        return (
            False,
            f"Недостаточно средств. Требуется {total_cost} {share.currency}, доступно {portfolio.cash_balance:.2f} {share.currency}.",
        )

    # Списание средств
    portfolio.cash_balance = round(portfolio.cash_balance - total_cost, 2)
    portfolio.save()

    # Обновление позиции
    position, created = PortfolioPosition.objects.get_or_create(
        portfolio=portfolio,
        share=share,
        defaults={"quantity": quantity, "average_buy_price": price},
    )
    if not created:
        prev_total = position.quantity * position.average_buy_price
        new_quantity = position.quantity + quantity
        new_average = (prev_total + total_cost) / new_quantity
        position.quantity = new_quantity
        position.average_buy_price = round(new_average, 2)
        position.save()

    # Запись транзакции
    PortfolioTransaction.objects.create(
        portfolio=portfolio,
        share=share,
        transaction_type="BUY",
        quantity=quantity,
        price=price,
        total_amount=total_cost,
    )

    return (
        True,
        f"Успешно куплено {quantity} шт. {share.ticker} на сумму {total_cost} {share.currency}.",
    )


@transaction.atomic
def sell_share(user, share_id, quantity):
    """
    Продажа акций из виртуального портфеля.
    Возвращает (успех: bool, сообщение: str).
    """
    if quantity <= 0:
        return False, "Количество акций должно быть больше нуля."

    portfolio = get_or_create_portfolio(user)
    try:
        position = PortfolioPosition.objects.get(portfolio=portfolio, share_id=share_id)
    except PortfolioPosition.DoesNotExist:
        return False, "В вашем портфеле нет акций этой компании."

    if position.quantity < quantity:
        return (
            False,
            f"Недостаточно акций для продажи. В наличии {position.quantity} шт., запрошено {quantity} шт.",
        )

    share = position.share
    price = share.last_price or position.average_buy_price
    total_proceeds = round(price * quantity, 2)

    # Начисление средств
    portfolio.cash_balance = round(portfolio.cash_balance + total_proceeds, 2)
    portfolio.save()

    # Обновление позиции
    if position.quantity == quantity:
        position.delete()
    else:
        position.quantity -= quantity
        position.save()

    # Запись транзакции
    PortfolioTransaction.objects.create(
        portfolio=portfolio,
        share=share,
        transaction_type="SELL",
        quantity=quantity,
        price=price,
        total_amount=total_proceeds,
    )

    return (
        True,
        f"Успешно продано {quantity} шт. {share.ticker} на сумму {total_proceeds} {share.currency}.",
    )
