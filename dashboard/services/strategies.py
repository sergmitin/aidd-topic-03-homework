from dashboard.models import StrategyLog, TradingStrategy, UserNotification
from dashboard.services.portfolio import execute_trade


def evaluate_strategies_for_share(share):
    """
    Проверяет активные стратегии для акции share и выполняет сделки, если условия совпали.
    """
    if share.last_price is None:
        return

    price = share.last_price
    strategies = TradingStrategy.objects.filter(share=share, is_active=True).select_related(
        "user"
    )

    for strategy in strategies:
        user = strategy.user
        should_buy = (
            strategy.buy_price is not None and price <= strategy.buy_price
        )
        should_sell = (
            strategy.sell_price is not None and price >= strategy.sell_price
        )

        if should_buy:
            success, msg = execute_trade(
                user=user, share=share, action="BUY", quantity=strategy.trade_quantity
            )
            StrategyLog.objects.create(
                strategy=strategy,
                action="BUY",
                price=price,
                quantity=strategy.trade_quantity,
                message=msg,
            )
            if success:
                strategy.total_executions += 1
                strategy.save(update_fields=["total_executions"])
                UserNotification.objects.create(
                    user=user,
                    share=share,
                    title=f"🤖 Робот исполнил покупку: {strategy.name}",
                    message=f"Стратегия '{strategy.name}' купила {strategy.trade_quantity} шт. {share.ticker} по {price} {share.currency}.",
                )

        elif should_sell:
            success, msg = execute_trade(
                user=user, share=share, action="SELL", quantity=strategy.trade_quantity
            )
            StrategyLog.objects.create(
                strategy=strategy,
                action="SELL",
                price=price,
                quantity=strategy.trade_quantity,
                message=msg,
            )
            if success:
                strategy.total_executions += 1
                strategy.save(update_fields=["total_executions"])
                UserNotification.objects.create(
                    user=user,
                    share=share,
                    title=f"🤖 Робот исполнил продажу: {strategy.name}",
                    message=f"Стратегия '{strategy.name}' продала {strategy.trade_quantity} шт. {share.ticker} по {price} {share.currency}.",
                )
