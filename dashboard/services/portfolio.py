from django.db import transaction
from dashboard.models import Portfolio, PortfolioPosition, PortfolioTransaction

INITIAL_BALANCE = 100000.0


def get_or_create_portfolio(user):
    """Возвращает существующий или создает новый виртуальный портфель для пользователя."""
    portfolio, _ = Portfolio.objects.get_or_create(user=user)
    return portfolio


def calculate_portfolio_summary(portfolio):
    """
    Рассчитывает финансовые показатели портфеля:
    - Общую стоимость активов (деньги + акции)
    - Текущую рыночную стоимость акций
    - Прибыль/убыток (PnL) относительно начального баланса 100 000 руб.
      (сохраняется и учитывается как при открытых, так и после закрытия позиций)
    """
    positions = portfolio.positions.filter(quantity__gt=0).select_related("share")
    shares_market_value = 0.0
    shares_total_cost = 0.0

    for pos in positions:
        shares_market_value += pos.current_value
        shares_total_cost += pos.total_cost

    total_portfolio_value = round(portfolio.balance + shares_market_value, 2)
    
    # Общий результат портфеля (Realized + Unrealized PnL)
    total_profit_loss = round(total_portfolio_value - INITIAL_BALANCE, 2)
    profit_loss_percent = round((total_profit_loss / INITIAL_BALANCE) * 100, 2)

    # Нереализованный PnL по текущим удерживаемым позициям
    unrealized_profit_loss = round(shares_market_value - shares_total_cost, 2)

    return {
        "balance": round(portfolio.balance, 2),
        "shares_market_value": round(shares_market_value, 2),
        "total_portfolio_value": total_portfolio_value,
        "total_profit_loss": total_profit_loss,
        "profit_loss_percent": profit_loss_percent,
        "unrealized_profit_loss": unrealized_profit_loss,
        "positions": positions,
    }


@transaction.atomic
def execute_trade(user, share, action, quantity):
    """
    Выполняет виртуальную сделку покупки или продажи акции.
    Возвращает (success: bool, message: str).
    """
    if quantity <= 0:
        return False, "Количество акций должно быть больше нуля."

    price = share.last_price
    if price is None or price <= 0:
        return False, f"Невозможно совершить сделку: у акции {share.ticker} не установлена цена."

    portfolio = get_or_create_portfolio(user)
    total_amount = round(price * quantity, 2)

    if action == "BUY":
        if portfolio.balance < total_amount:
            return (
                False,
                f"Недостаточно средств. Требуется {total_amount} {share.currency}, доступно {round(portfolio.balance, 2)} {share.currency}.",
            )

        portfolio.balance -= total_amount
        portfolio.save(update_fields=["balance"])

        position, created = PortfolioPosition.objects.get_or_create(
            portfolio=portfolio, share=share
        )
        if created or position.quantity == 0:
            position.quantity = quantity
            position.average_buy_price = price
        else:
            total_cost_before = position.quantity * position.average_buy_price
            new_quantity = position.quantity + quantity
            new_average = (total_cost_before + total_amount) / new_quantity
            position.quantity = new_quantity
            position.average_buy_price = round(new_average, 2)
        position.save()

        PortfolioTransaction.objects.create(
            portfolio=portfolio,
            share=share,
            transaction_type="BUY",
            quantity=quantity,
            price=price,
            total_amount=total_amount,
        )
        return (
            True,
            f"Успешно куплено {quantity} шт. {share.ticker} по цене {price} {share.currency}.",
        )

    elif action == "SELL":
        try:
            position = PortfolioPosition.objects.get(portfolio=portfolio, share=share)
        except PortfolioPosition.DoesNotExist:
            return False, f"В вашем портфеле нет акций {share.ticker} для продажи."

        if position.quantity < quantity:
            return (
                False,
                f"Недостаточно акций. В наличии: {position.quantity} шт., запрошено на продажу: {quantity} шт.",
            )

        portfolio.balance += total_amount
        portfolio.save(update_fields=["balance"])

        position.quantity -= quantity
        position.save(update_fields=["quantity"])

        PortfolioTransaction.objects.create(
            portfolio=portfolio,
            share=share,
            transaction_type="SELL",
            quantity=quantity,
            price=price,
            total_amount=total_amount,
        )
        return (
            True,
            f"Успешно продано {quantity} шт. {share.ticker} по цене {price} {share.currency}.",
        )

    return False, "Неизвестный тип операции."
