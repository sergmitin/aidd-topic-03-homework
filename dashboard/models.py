from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Share(models.Model):
    """Акция"""

    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.FloatField(blank=True, null=True, verbose_name="Текущая цена")
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self):
        return f"{self.name} ({self.ticker})"


# ==========================================
# Модуль 1: Персональный мониторинг и алерты
# ==========================================

class WatchlistItem(models.Model):
    """Персональный список наблюдения за акциями"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="watchlist_items"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="watchlisted_by"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Элемент списка наблюдения"
        verbose_name_plural = "Список наблюдения"
        unique_together = ("user", "share")
        ordering = ["-added_at"]


class PriceAlert(models.Model):
    """Целевые ценовые уровни и уведомления"""

    CONDITION_CHOICES = (
        ("above", "Выше или равно"),
        ("below", "Ниже или равно"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="price_alerts"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="price_alerts"
    )
    target_price = models.FloatField(verbose_name="Целевая цена")
    condition = models.CharField(
        max_length=10, choices=CONDITION_CHOICES, default="above"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_triggered = models.BooleanField(default=False, verbose_name="Сработал")
    created_at = models.DateTimeField(auto_now_add=True)
    triggered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ценовое уведомление"
        verbose_name_plural = "Ценовые уведомления"
        ordering = ["-created_at"]


class UserNotification(models.Model):
    """Внутрисистемные уведомления пользователя"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-created_at"]


# ==========================================
# Модуль 2: Виртуальный инвестиционный портфель
# ==========================================

class Portfolio(models.Model):
    """Инвестиционный портфель пользователя"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="portfolios"
    )
    name = models.CharField(max_length=255, default="Основной портфель")
    cash_balance = models.FloatField(default=100000.0, verbose_name="Свободные средства")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Инвестиционный портфель"
        verbose_name_plural = "Инвестиционные портфели"

    @property
    def total_positions_value(self):
        """Текущая стоимость всех удерживаемых акций"""
        return sum(pos.current_value for pos in self.positions.all())

    @property
    def total_portfolio_value(self):
        """Суммарная стоимость портфеля (деньги + акции)"""
        return round(self.cash_balance + self.total_positions_value, 2)

    @property
    def total_profit_loss(self):
        """
        Суммарная прибыль / убыток всего портфеля относительно начального депозита (100 000 RUB).
        Учитывает как нереализованный P&L по открытым акциям, так и реализованный профит от закрытых сделок и роботов.
        """
        initial_deposit = 100000.0
        return round(self.total_portfolio_value - initial_deposit, 2)

    @property
    def total_profit_loss_percent(self):
        """Суммарная доходность портфеля в процентах от начального депозита"""
        initial_deposit = 100000.0
        return round((self.total_profit_loss / initial_deposit) * 100, 2)


class PortfolioPosition(models.Model):
    """Позиция (акции одного эмитента) в портфеле"""

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="positions"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="portfolio_positions"
    )
    quantity = models.IntegerField(default=0, verbose_name="Количество")
    average_buy_price = models.FloatField(default=0.0, verbose_name="Средняя цена покупки")

    class Meta:
        verbose_name = "Позиция в портфеле"
        verbose_name_plural = "Позиции в портфеле"
        unique_together = ("portfolio", "share")

    @property
    def total_invested(self):
        return round(self.quantity * self.average_buy_price, 2)

    @property
    def current_value(self):
        price = self.share.last_price or self.average_buy_price
        return round(self.quantity * price, 2)

    @property
    def profit_loss(self):
        price = self.share.last_price or self.average_buy_price
        return round((price - self.average_buy_price) * self.quantity, 2)

    @property
    def profit_loss_percent(self):
        if self.average_buy_price == 0:
            return 0.0
        price = self.share.last_price or self.average_buy_price
        return round(((price / self.average_buy_price) - 1.0) * 100, 2)


class PortfolioTransaction(models.Model):
    """Журнал операций (сделок) с ценными бумагами"""

    TYPE_CHOICES = (
        ("BUY", "Покупка"),
        ("SELL", "Продажа"),
    )

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="transactions"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.IntegerField(verbose_name="Количество")
    price = models.FloatField(verbose_name="Цена исполнения")
    total_amount = models.FloatField(verbose_name="Сумма сделки")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Сделка"
        verbose_name_plural = "История сделок"
        ordering = ["-created_at"]


# ==========================================
# Модуль 3: История изменения рыночных цен
# ==========================================

class SharePriceHistory(models.Model):
    """История изменения рыночных цен акций в базе данных"""

    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="price_history"
    )
    price = models.FloatField(verbose_name="Рыночная цена")
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Историческая котировка"
        verbose_name_plural = "История котировок"
        ordering = ["-recorded_at"]


# ==========================================
# Модуль 4: Симулятор инвестиционных стратегий
# ==========================================

class TradingStrategy(models.Model):
    """Автоматическая стратегия торговли акцией"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="strategies"
    )
    name = models.CharField(max_length=255, verbose_name="Название стратегии")
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="strategies"
    )
    buy_threshold = models.FloatField(verbose_name="Порог покупки (если цена <=)")
    sell_threshold = models.FloatField(verbose_name="Порог продажи (если цена >=)")
    trade_quantity = models.IntegerField(default=1, verbose_name="Объем сделки (шт)")

    initial_capital = models.FloatField(default=50000.0, verbose_name="Стартовый капитал")
    current_capital = models.FloatField(default=50000.0, verbose_name="Текущий капитал")
    shares_held = models.IntegerField(default=0, verbose_name="Удерживаемых акций")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Инвестиционная стратегия"
        verbose_name_plural = "Инвестиционные стратегии"
        ordering = ["-created_at"]

    @property
    def current_position_shares(self):
        return self.shares_held

    @property
    def total_value(self):
        share_price = self.share.last_price or self.buy_threshold
        return round(self.current_capital + (self.shares_held * share_price), 2)

    @property
    def profit_loss(self):
        return round(self.total_value - self.initial_capital, 2)

    @property
    def profit_loss_percent(self):
        if self.initial_capital == 0:
            return 0.0
        return round((self.profit_loss / self.initial_capital) * 100, 2)

    @property
    def total_trades_count(self):
        return self.execution_logs.count()

    @property
    def successful_trades_count(self):
        return self.execution_logs.filter(profit_loss__gt=0).count()


class StrategyExecutionLog(models.Model):
    """Журнал исполнения стратегий"""

    strategy = models.ForeignKey(
        TradingStrategy, on_delete=models.CASCADE, related_name="execution_logs"
    )
    action = models.CharField(max_length=10, choices=(("BUY", "Покупка"), ("SELL", "Продажа")))
    price = models.FloatField()
    quantity = models.IntegerField()
    total_amount = models.FloatField()
    profit_loss = models.FloatField(default=0.0)
    comment = models.CharField(max_length=255, blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лог исполнения стратегии"
        verbose_name_plural = "Логи исполнения стратегий"
        ordering = ["-executed_at"]

    @property
    def created_at(self):
        return self.executed_at

    @property
    def message(self):
        return self.comment
