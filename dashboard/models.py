from django.contrib.auth import get_user_model
from django.db import models

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
        return f"{self.ticker} ({self.name})"


class PriceHistory(models.Model):
    """История изменения рыночных цен"""

    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="price_history", verbose_name="Акция"
    )
    price = models.FloatField(verbose_name="Цена")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Время фиксации")
    source = models.CharField(
        max_length=50, default="market", verbose_name="Источник котировки"
    )

    class Meta:
        verbose_name = "История цены"
        verbose_name_plural = "История цен"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.share.ticker} - {self.price} @ {self.created_at:%Y-%m-%d %H:%M}"


class WatchlistItem(models.Model):
    """Персональный мониторинг акций (Watchlist и ценовые алерты)"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="watchlist", verbose_name="Пользователь"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="watchlists", verbose_name="Акция"
    )
    target_price_high = models.FloatField(
        null=True, blank=True, verbose_name="Целевая цена (верхняя планка)"
    )
    target_price_low = models.FloatField(
        null=True, blank=True, verbose_name="Целевая цена (нижняя планка)"
    )
    last_notified_type = models.CharField(
        max_length=20, null=True, blank=True, verbose_name="Последнее отправленное уведомление"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Элемент списка наблюдения"
        verbose_name_plural = "Списки наблюдения"
        unique_together = ("user", "share")

    def __str__(self):
        return f"{self.user.username} -> {self.share.ticker}"


class UserNotification(models.Model):
    """Системные уведомления пользователя об алертах и стратегиях"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications", verbose_name="Пользователь"
    )
    share = models.ForeignKey(
        Share, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Акция"
    )
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Текст уведомления")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class Portfolio(models.Model):
    """Виртуальный инвестиционный портфель пользователя"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="portfolio", verbose_name="Пользователь"
    )
    balance = models.FloatField(default=100000.0, verbose_name="Свободные денежные средства")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата открытия")

    class Meta:
        verbose_name = "Инвестиционный портфель"
        verbose_name_plural = "Инвестиционные портфели"

    def __str__(self):
        return f"Портфель {self.user.username}"


class PortfolioPosition(models.Model):
    """Позиция акции в портфеле"""

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="positions", verbose_name="Портфель"
    )
    share = models.ForeignKey(Share, on_delete=models.CASCADE, verbose_name="Акция")
    quantity = models.IntegerField(default=0, verbose_name="Количество бумаг")
    average_buy_price = models.FloatField(default=0.0, verbose_name="Средняя цена покупки")

    class Meta:
        verbose_name = "Позиция в портфеле"
        verbose_name_plural = "Позиции в портфеле"
        unique_together = ("portfolio", "share")

    @property
    def current_value(self):
        price = self.share.last_price or self.average_buy_price
        return round(self.quantity * price, 2)

    @property
    def total_cost(self):
        return round(self.quantity * self.average_buy_price, 2)

    @property
    def profit_loss(self):
        return round(self.current_value - self.total_cost, 2)

    @property
    def profit_loss_percent(self):
        if self.total_cost > 0:
            return round((self.profit_loss / self.total_cost) * 100, 2)
        return 0.0


class PortfolioTransaction(models.Model):
    """История операций купли/продажи акций в портфеле"""

    TRANSACTION_TYPES = (
        ("BUY", "Покупка"),
        ("SELL", "Продажа"),
    )

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="transactions", verbose_name="Портфель"
    )
    share = models.ForeignKey(Share, on_delete=models.CASCADE, verbose_name="Акция")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name="Тип сделки")
    quantity = models.IntegerField(verbose_name="Количество")
    price = models.FloatField(verbose_name="Цена исполнения")
    total_amount = models.FloatField(verbose_name="Сумма сделки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время сделки")

    class Meta:
        verbose_name = "Сделка"
        verbose_name_plural = "История сделок"
        ordering = ["-created_at"]


class TradingStrategy(models.Model):
    """Симулятор торговых инвестиционных стратегий"""

    STRATEGY_TYPES = (
        ("PRICE_THRESHOLD", "Покупка при падении ниже уровня / Продажа выше уровня"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="strategies", verbose_name="Пользователь"
    )
    share = models.ForeignKey(Share, on_delete=models.CASCADE, verbose_name="Акция")
    name = models.CharField(max_length=255, verbose_name="Название стратегии")
    strategy_type = models.CharField(
        max_length=50, choices=STRATEGY_TYPES, default="PRICE_THRESHOLD", verbose_name="Тип стратегии"
    )
    buy_price = models.FloatField(null=True, blank=True, verbose_name="Цена покупки (ниже или равно)")
    sell_price = models.FloatField(null=True, blank=True, verbose_name="Цена продажи (выше или равно)")
    trade_quantity = models.IntegerField(default=1, verbose_name="Количество акций в сделке")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    total_executions = models.IntegerField(default=0, verbose_name="Количество сработавших сделок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Торговая стратегия"
        verbose_name_plural = "Торговые стратегии"
        ordering = ["-created_at"]


class StrategyLog(models.Model):
    """Журнал операций симулятора стратегий"""

    strategy = models.ForeignKey(
        TradingStrategy, on_delete=models.CASCADE, related_name="logs", verbose_name="Стратегия"
    )
    action = models.CharField(max_length=20, verbose_name="Действие (BUY/SELL/HOLD)")
    price = models.FloatField(verbose_name="Цена фиксации")
    quantity = models.IntegerField(verbose_name="Количество")
    message = models.CharField(max_length=255, verbose_name="Результат проверки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время события")

    class Meta:
        verbose_name = "Лог стратегии"
        verbose_name_plural = "Логи стратегий"
        ordering = ["-created_at"]
