import logging
from django.db import transaction

from dashboard.models import StrategyExecutionLog, TradingStrategy
from dashboard.services.portfolio import get_or_create_portfolio, PortfolioPosition, PortfolioTransaction

logger = logging.getLogger("main")


@transaction.atomic
def evaluate_strategies_for_share(share, current_price):
    """
    Автоматическая проверка и исполнение активных стратегий по акции.
    Моделирует сделки покупки и продажи по заданным условиям
    и синхронизирует их с основным портфелем пользователя.
    """
    strategies = TradingStrategy.objects.filter(share=share, is_active=True).select_related("user")
    executions_count = 0

    for strat in strategies:
        portfolio = get_or_create_portfolio(strat.user)

        # Условие 1: Покупка (цена <= buy_threshold)
        if current_price <= strat.buy_threshold:
            cost = round(strat.trade_quantity * current_price, 2)
            if strat.current_capital >= cost:
                strat.current_capital = round(strat.current_capital - cost, 2)
                strat.shares_held += strat.trade_quantity
                strat.save()

                StrategyExecutionLog.objects.create(
                    strategy=strat,
                    action="BUY",
                    price=current_price,
                    quantity=strat.trade_quantity,
                    total_amount=cost,
                    profit_loss=0.0,
                    comment=f"Исполнена автопокупка: цена {current_price} <= порога {strat.buy_threshold}",
                )

                # Синхронизация с портфелем: списание денег и добавление позиции
                if portfolio.cash_balance >= cost:
                    portfolio.cash_balance = round(portfolio.cash_balance - cost, 2)
                    portfolio.save()

                    pos, created = PortfolioPosition.objects.get_or_create(
                        portfolio=portfolio,
                        share=share,
                        defaults={"quantity": strat.trade_quantity, "average_buy_price": current_price},
                    )
                    if not created:
                        prev_total = pos.quantity * pos.average_buy_price
                        new_qty = pos.quantity + strat.trade_quantity
                        pos.average_buy_price = round((prev_total + cost) / new_qty, 2)
                        pos.quantity = new_qty
                        pos.save()

                    PortfolioTransaction.objects.create(
                        portfolio=portfolio,
                        share=share,
                        transaction_type="BUY",
                        quantity=strat.trade_quantity,
                        price=current_price,
                        total_amount=cost,
                    )

                executions_count += 1
                logger.info(f"Стратегия '{strat.name}': совершена покупка {strat.trade_quantity} {share.ticker}")

        # Условие 2: Продажа (цена >= sell_threshold)
        elif current_price >= strat.sell_threshold:
            if strat.shares_held >= strat.trade_quantity:
                proceeds = round(strat.trade_quantity * current_price, 2)
                estimated_buy_cost = strat.trade_quantity * strat.buy_threshold
                profit = round(proceeds - estimated_buy_cost, 2)

                strat.current_capital = round(strat.current_capital + proceeds, 2)
                strat.shares_held -= strat.trade_quantity
                strat.save()

                StrategyExecutionLog.objects.create(
                    strategy=strat,
                    action="SELL",
                    price=current_price,
                    quantity=strat.trade_quantity,
                    total_amount=proceeds,
                    profit_loss=profit,
                    comment=f"Исполнена автопродажа: цена {current_price} >= порога {strat.sell_threshold}",
                )

                # Синхронизация с портфелем: зачисление выручки и списание акций
                portfolio.cash_balance = round(portfolio.cash_balance + proceeds, 2)
                portfolio.save()

                try:
                    pos = PortfolioPosition.objects.get(portfolio=portfolio, share=share)
                    if pos.quantity <= strat.trade_quantity:
                        pos.delete()
                    else:
                        pos.quantity -= strat.trade_quantity
                        pos.save()
                except PortfolioPosition.DoesNotExist:
                    pass

                PortfolioTransaction.objects.create(
                    portfolio=portfolio,
                    share=share,
                    transaction_type="SELL",
                    quantity=strat.trade_quantity,
                    price=current_price,
                    total_amount=proceeds,
                )

                executions_count += 1
                logger.info(f"Стратегия '{strat.name}': совершена продажа {strat.trade_quantity} {share.ticker}")

    return executions_count


evaluate_trading_strategies = evaluate_strategies_for_share
