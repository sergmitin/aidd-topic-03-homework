from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import (
    PriceHistory,
    Portfolio,
    PortfolioPosition,
    PortfolioTransaction,
    Share,
    StrategyLog,
    TradingStrategy,
    UserNotification,
    WatchlistItem,
)
from dashboard.services.alerts import check_price_alerts_for_share
from dashboard.services.portfolio import (
    calculate_portfolio_summary,
    execute_trade,
    get_or_create_portfolio,
)
from dashboard.services.price_history import (
    get_price_statistics,
    record_price_change,
)
from dashboard.services.strategies import evaluate_strategies_for_share
from dashboard.tasks import process_share_price_update

User = get_user_model()


class DashboardAPITests(APITestCase):
    """Тестирование REST API"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="api_user@example.com",
            email="api_user@example.com",
            password="SecurePassword123!",
        )
        self.client.force_authenticate(user=self.user)

        self.apple_share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=150.0,
            is_trend_high=True,
        )

    def test_share_list(self):
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_share_detail(self):
        response = self.client.get(f"/api/v1/shares/{self.apple_share.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ticker"], "AAPL")

    def test_share_create(self):
        payload = {
            "figi": "BBG000TEST1",
            "isin": "RU000TEST1",
            "name": "Test Share",
            "ticker": "TEST1",
            "currency": "rub",
            "uid": "uid-test-1",
        }
        response = self.client.post("/api/v1/shares/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Share.objects.filter(ticker="TEST1").exists())


class NewFeaturesTests(TestCase):
    """Тестирование функциональности Задания №4"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="investor@example.com",
            email="investor@example.com",
            password="Password123!",
        )
        self.share = Share.objects.create(
            figi="BBG004730N88",
            isin="RU0009029540",
            name="Сбербанк",
            ticker="SBER",
            currency="rub",
            uid="uid-sber-123",
            last_price=250.0,
            is_trend_high=True,
        )

    # 1. Тестирование персонального мониторинга (Watchlist и алерты)
    def test_watchlist_alert_high_and_deduplication(self):
        item = WatchlistItem.objects.create(
            user=self.user,
            share=self.share,
            target_price_low=200.0,
            target_price_high=300.0,
        )

        # Цена растет до 310 (превышает верхний порог 300)
        self.share.last_price = 310.0
        check_price_alerts_for_share(self.share)

        notifications = UserNotification.objects.filter(user=self.user, share=self.share)
        self.assertEqual(notifications.count(), 1)
        self.assertIn("Достигнут верхний целевой уровень", notifications.first().title)

        # Повторная проверка при той же цене НЕ должна создавать дубликатов!
        check_price_alerts_for_share(self.share)
        self.assertEqual(notifications.count(), 1)

    # 2. Тестирование виртуального инвестиционного портфеля
    def test_portfolio_buy_and_sell(self):
        portfolio = get_or_create_portfolio(self.user)
        self.assertEqual(portfolio.balance, 100000.0)

        # Покупка 10 акций по 250 руб = 2500 руб.
        success, msg = execute_trade(self.user, self.share, action="BUY", quantity=10)
        self.assertTrue(success)
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.balance, 97500.0)

        position = PortfolioPosition.objects.get(portfolio=portfolio, share=self.share)
        self.assertEqual(position.quantity, 10)
        self.assertEqual(position.average_buy_price, 250.0)

        # Продажа 4 акций
        success, msg = execute_trade(self.user, self.share, action="SELL", quantity=4)
        self.assertTrue(success)
        position.refresh_from_db()
        portfolio.refresh_from_db()
        self.assertEqual(position.quantity, 6)
        self.assertEqual(portfolio.balance, 98500.0)

        # Продажа остальных 6 акций с убытком (цена упала до 200 руб)
        self.share.last_price = 200.0
        self.share.save(update_fields=["last_price"])
        success, msg = execute_trade(self.user, self.share, action="SELL", quantity=6)
        self.assertTrue(success)

        portfolio.refresh_from_db()
        # Все акции проданы, но убыток должен сохраняться в балансе и PnL портфеля!
        summary = calculate_portfolio_summary(portfolio)
        self.assertEqual(summary["shares_market_value"], 0.0)
        # Было 100 000, потратили 2500, вернули 1000 + 1200 = 2200, баланс = 99700, убыток = -300 руб.
        self.assertEqual(summary["balance"], 99700.0)
        self.assertEqual(summary["total_profit_loss"], -300.0)

    # 3. Тестирование истории изменения цен
    def test_price_history_and_statistics(self):
        # Записываем историю котировок
        record_price_change(self.share, 200.0, source="manual")
        record_price_change(self.share, 220.0, source="manual")
        record_price_change(self.share, 250.0, source="manual")

        self.assertEqual(PriceHistory.objects.filter(share=self.share).count(), 3)

        stats = get_price_statistics(self.share, days=30)
        self.assertEqual(stats["start_price"], 200.0)
        self.assertEqual(stats["current_price"], 250.0)
        self.assertEqual(stats["abs_change"], 50.0)
        self.assertEqual(stats["percent_change"], 25.0)

    # 4. Тестирование симулятора торговых стратегий
    def test_trading_strategy_execution(self):
        # Создаем стратегию: покупать, если цена упадет до 220 или ниже
        strategy = TradingStrategy.objects.create(
            user=self.user,
            share=self.share,
            name="Buy Sber Dip",
            strategy_type="PRICE_THRESHOLD",
            buy_price=220.0,
            trade_quantity=5,
            is_active=True,
        )

        # Цена падает до 210 руб
        self.share.last_price = 210.0
        evaluate_strategies_for_share(self.share)

        strategy.refresh_from_db()
        self.assertEqual(strategy.total_executions, 1)

        position = PortfolioPosition.objects.get(
            portfolio__user=self.user, share=self.share
        )
        self.assertEqual(position.quantity, 5)



class AllViewsEndToEndTests(TestCase):
    """
    Сквозное тестирование всех view и шаблонов приложения.
    Гарантирует отсутствие ошибок OperationalError, KeyError, TemplateSyntaxError и 500 на всех страницах.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="tester@example.com",
            email="tester@example.com",
            password="StrongPassword123!",
        )
        self.share = Share.objects.create(
            figi="BBG000TEST99",
            isin="RU000TEST999",
            name="Газпром",
            ticker="GAZP",
            currency="rub",
            uid="uid-gazp-99",
            last_price=150.0,
            is_trend_high=True,
        )

    def test_public_views(self):
        # 1. Главная страница
        res = self.client.get(reverse("dashboard:index"))
        self.assertEqual(res.status_code, 200)

        # 2. Детальная страница акции
        res = self.client.get(reverse("dashboard:detail", kwargs={"pk": self.share.id}))
        self.assertEqual(res.status_code, 200)

        # 3. Страница истории цен
        res = self.client.get(reverse("dashboard:price_history", kwargs={"pk": self.share.id}))
        self.assertEqual(res.status_code, 200)

    def test_authenticated_views(self):
        self.client.force_login(self.user)

        # Создаем уведомление с привязанной акцией
        UserNotification.objects.create(
            user=self.user,
            share=self.share,
            title="Тестовый алерт",
            message="Цена достигла целевого значения",
        )

        # 1. Страница уведомлений (где ранее была ошибка OperationalError)
        res = self.client.get(reverse("dashboard:notifications"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Тестовый алерт")

        # 2. Страница портфеля
        res = self.client.get(reverse("dashboard:portfolio"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "100000")

        # 3. Страница истории транзакций
        res = self.client.get(reverse("dashboard:portfolio_transactions"))
        self.assertEqual(res.status_code, 200)

        # 4. Страница мониторинга (Watchlist)
        res = self.client.get(reverse("dashboard:watchlist"))
        self.assertEqual(res.status_code, 200)

        # 5. Страница стратегий
        res = self.client.get(reverse("dashboard:strategies"))
        self.assertEqual(res.status_code, 200)

        # 6. Форма редактирования акции (с ручным изменением цены)
        res = self.client.get(reverse("dashboard:update", kwargs={"pk": self.share.id}))
        self.assertEqual(res.status_code, 200)

        # 7. POST запрос ручного изменения цены через форму
        res = self.client.post(
            reverse("dashboard:update", kwargs={"pk": self.share.id}),
            {
                "figi": self.share.figi,
                "isin": self.share.isin,
                "name": self.share.name,
                "ticker": self.share.ticker,
                "currency": self.share.currency,
                "uid": self.share.uid,
                "last_price": 185.50,
            },
        )
        self.assertRedirects(res, reverse("dashboard:index"))
        self.share.refresh_from_db()
        self.assertEqual(self.share.last_price, 185.50)

        # 8. POST запрос тика рынка
        res = self.client.post(reverse("dashboard:simulate_tick"))
        self.assertEqual(res.status_code, 302)
