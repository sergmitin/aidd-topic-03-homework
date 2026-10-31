from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import Share
from dashboard.tasks import update_last_price

User = get_user_model()


class DashboardTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="tester@example.com",
            email="tester@example.com",
            password="TestPassword123!",
        )
        self.apple_share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.50,
            is_trend_high=True,
        )

        self.second_company = {
            "figi": "BBG000B9XRY5",
            "isin": "US0378331004",
            "name": "Company_test",
            "ticker": "TESTTEST",
            "currency": "usd",
            "uid": "a9eb4238-eba9-488c-b102-b6140fd08e39",
            "last_price": 1.50,
            "is_trend_high": False,
        }

    # --- HTML Views Tests ---

    def test_share_list_html(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "AAPL")
        self.assertContains(response, "Apple")

    def test_share_detail_html(self):
        response = self.client.get(
            reverse("dashboard:detail", kwargs={"pk": self.apple_share.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.apple_share.name)
        # Проверяем, что график Plotly успешно сгенерирован и включен в HTML
        self.assertContains(response, "plotly")

    def test_share_detail_html_not_found(self):
        response = self.client.get(
            reverse("dashboard:detail", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_create_html_unauthenticated_redirect(self):
        response = self.client.get(reverse("dashboard:create"))
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_share_create_html_authenticated(self):
        self.client.login(username="tester@example.com", password="TestPassword123!")
        response = self.client.get(reverse("dashboard:create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        post_data = {
            "figi": "BBG000B9XRY9",
            "isin": "RU0009029540",
            "name": "Sberbank",
            "ticker": "SBER",
            "currency": "RUB",
            "uid": "uid-sber-123",
            "last_price": 280.0,
            "is_trend_high": True,
        }
        create_resp = self.client.post(reverse("dashboard:create"), post_data)
        self.assertRedirects(create_resp, reverse("dashboard:index"))
        self.assertTrue(Share.objects.filter(ticker="SBER").exists())

    def test_share_update_html_unauthenticated_redirect(self):
        response = self.client.get(
            reverse("dashboard:update", kwargs={"pk": self.apple_share.id})
        )
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_share_update_html_authenticated(self):
        self.client.login(username="tester@example.com", password="TestPassword123!")
        post_data = {
            "figi": self.apple_share.figi,
            "isin": self.apple_share.isin,
            "name": "Apple Updated",
            "ticker": self.apple_share.ticker,
            "currency": self.apple_share.currency,
            "uid": self.apple_share.uid,
            "last_price": 150.0,
            "is_trend_high": True,
        }
        response = self.client.post(
            reverse("dashboard:update", kwargs={"pk": self.apple_share.id}), post_data
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.apple_share.refresh_from_db()
        self.assertEqual(self.apple_share.name, "Apple Updated")

    def test_share_delete_html_unauthenticated_redirect(self):
        response = self.client.post(
            reverse("dashboard:delete", kwargs={"pk": self.apple_share.id})
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertTrue(Share.objects.filter(id=self.apple_share.id).exists())

    def test_share_delete_html_authenticated(self):
        self.client.login(username="tester@example.com", password="TestPassword123!")
        response = self.client.post(
            reverse("dashboard:delete", kwargs={"pk": self.apple_share.id})
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertFalse(Share.objects.filter(id=self.apple_share.id).exists())

    # --- REST API Tests ---

    def test_share_list_api(self):
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        apple = response.json().get("results")[0]
        self.assertEqual(apple["ticker"], self.apple_share.ticker)

    def test_share_detail_api(self):
        response = self.client.get(f"/api/v1/shares/{self.apple_share.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_share_detail_invalid_api(self):
        response = self.client.get("/api/v1/shares/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_create_api(self):
        response = self.client.post(
            "/api/v1/shares/", self.second_company, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Share.objects.count(), 2)

    def test_share_create_invalid_api(self):
        response = self.client.post(
            "/api/v1/shares/", {"figi": "BBG000B9XRY5"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_update_api(self):
        response = self.client.put(
            f"/api/v1/shares/{self.apple_share.id}/",
            {
                "id": self.apple_share.id,
                "figi": self.apple_share.figi,
                "isin": self.apple_share.isin,
                "name": "Apple Renamed",
                "ticker": self.apple_share.ticker,
                "currency": self.apple_share.currency,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.apple_share.refresh_from_db()
        self.assertEqual(self.apple_share.name, "Apple Renamed")

    def test_share_delete_api(self):
        response = self.client.delete(f"/api/v1/shares/{self.apple_share.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Share.objects.count(), 0)

    # --- Management Commands and Tasks Tests ---

    def test_add_shares_command(self):
        call_command("add_shares")
        # Проверяем, что акции инициализированы
        self.assertGreaterEqual(Share.objects.count(), 5)

    def test_update_last_price_task_without_token(self):
        # Задача не должна падать с исключением при отсутствии токена
        update_last_price()
        self.assertTrue(Share.objects.filter(id=self.apple_share.id).exists())


class Task4WatchlistAndAlertsTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="investor@example.com",
            email="investor@example.com",
            password="StrongPassword123!",
        )
        self.share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple Inc.",
            ticker="AAPL",
            currency="USD",
            uid="uid-apple-1",
            last_price=150.0,
            is_trend_high=True,
        )

    def test_watchlist_toggle(self):
        self.client.login(username="investor@example.com", password="StrongPassword123!")
        
        # 1. Добавление в watchlist
        resp1 = self.client.post(reverse("dashboard:watchlist_toggle", kwargs={"share_id": self.share.id}))
        self.assertEqual(resp1.status_code, status.HTTP_302_FOUND)
        from dashboard.models import WatchlistItem
        self.assertTrue(WatchlistItem.objects.filter(user=self.user, share=self.share).exists())

        # 2. Удаление из watchlist при повторном клике
        resp2 = self.client.post(reverse("dashboard:watchlist_toggle", kwargs={"share_id": self.share.id}))
        self.assertEqual(resp2.status_code, status.HTTP_302_FOUND)
        self.assertFalse(WatchlistItem.objects.filter(user=self.user, share=self.share).exists())

    def test_price_alert_creation_and_trigger(self):
        self.client.login(username="investor@example.com", password="StrongPassword123!")
        from dashboard.models import PriceAlert, UserNotification
        from dashboard.services.alerts import check_and_trigger_alerts

        # Создаем алерт: уведомить если цена >= 160.0
        post_data = {
            "share_id": self.share.id,
            "condition": "above",
            "target_price": 160.0,
        }
        resp = self.client.post(reverse("dashboard:create_alert"), post_data)
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        alert = PriceAlert.objects.get(user=self.user, share=self.share)
        self.assertFalse(alert.is_triggered)

        # Проверяем при цене 155 (не должно сработать)
        check_and_trigger_alerts(self.share, 155.0)
        alert.refresh_from_db()
        self.assertFalse(alert.is_triggered)
        self.assertEqual(UserNotification.objects.filter(user=self.user).count(), 0)

        # Проверяем при цене 165 (должно сработать)
        check_and_trigger_alerts(self.share, 165.0)
        alert.refresh_from_db()
        self.assertTrue(alert.is_triggered)
        self.assertEqual(UserNotification.objects.filter(user=self.user).count(), 1)

        # Повторный тик не должен плодить дубликаты уведомлений
        check_and_trigger_alerts(self.share, 170.0)
        self.assertEqual(UserNotification.objects.filter(user=self.user).count(), 1)


class Task4PortfolioTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="trader@example.com",
            email="trader@example.com",
            password="StrongPassword123!",
        )
        self.share = Share.objects.create(
            figi="BBG004730N88",
            isin="RU0009029540",
            name="Sberbank",
            ticker="SBER",
            currency="RUB",
            uid="uid-sber-1",
            last_price=200.0,
            is_trend_high=True,
        )

    def test_buy_and_sell_shares(self):
        self.client.login(username="trader@example.com", password="StrongPassword123!")
        from dashboard.models import Portfolio, PortfolioPosition, PortfolioTransaction

        # 1. Покупка 10 акций по цене 200.0 = 2000.0 RUB
        resp_buy = self.client.post(
            reverse("dashboard:portfolio_buy"),
            {"share_id": self.share.id, "quantity": 10},
        )
        self.assertEqual(resp_buy.status_code, status.HTTP_302_FOUND)

        portfolio = Portfolio.objects.get(user=self.user)
        self.assertEqual(portfolio.cash_balance, 100000.0 - 2000.0)
        pos = PortfolioPosition.objects.get(portfolio=portfolio, share=self.share)
        self.assertEqual(pos.quantity, 10)
        self.assertEqual(pos.average_buy_price, 200.0)
        self.assertEqual(PortfolioTransaction.objects.filter(portfolio=portfolio).count(), 1)

        # 2. Попытка купить больше чем доступно денег
        resp_over = self.client.post(
            reverse("dashboard:portfolio_buy"),
            {"share_id": self.share.id, "quantity": 1000000},
        )
        self.assertEqual(resp_over.status_code, status.HTTP_302_FOUND)
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.cash_balance, 98000.0)  # Баланс не изменился

        # 3. Продажа части акций (4 шт.)
        resp_sell = self.client.post(
            reverse("dashboard:portfolio_sell"),
            {"share_id": self.share.id, "quantity": 4},
        )
        self.assertEqual(resp_sell.status_code, status.HTTP_302_FOUND)
        portfolio.refresh_from_db()
        pos.refresh_from_db()
        self.assertEqual(pos.quantity, 6)
        self.assertEqual(portfolio.cash_balance, 98000.0 + (4 * 200.0))

        # 4. Продажа всех оставшихся акций (6 шт.)
        resp_sell_all = self.client.post(
            reverse("dashboard:portfolio_sell"),
            {"share_id": self.share.id, "quantity": 6},
        )
        self.assertEqual(resp_sell_all.status_code, status.HTTP_302_FOUND)
        self.assertFalse(PortfolioPosition.objects.filter(portfolio=portfolio, share=self.share).exists())


class Task4AnalyticsAndStrategyTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="quant@example.com",
            email="quant@example.com",
            password="StrongPassword123!",
        )
        self.share = Share.objects.create(
            figi="BBG004731032",
            isin="RU0009029541",
            name="Gazprom",
            ticker="GAZP",
            currency="RUB",
            uid="uid-gazp-1",
            last_price=150.0,
            is_trend_high=False,
        )

    def test_price_history_and_analytics(self):
        from dashboard.services.price_history import record_price_history, get_price_analytics

        # Записываем историю цен
        record_price_history(self.share, 140.0)
        record_price_history(self.share, 150.0)
        record_price_history(self.share, 160.0)

        analytics = get_price_analytics(self.share, period="1d")
        self.assertEqual(analytics["count"], 3)
        self.assertEqual(analytics["first_price"], 140.0)
        self.assertEqual(analytics["last_price"], 160.0)
        self.assertEqual(analytics["min_price"], 140.0)
        self.assertEqual(analytics["max_price"], 160.0)
        self.assertEqual(analytics["delta"], 20.0)
        self.assertAlmostEqual(analytics["delta_percent"], 14.29, places=2)
        self.assertEqual(analytics["trend"], "up")

    def test_trading_strategy_simulator(self):
        self.client.login(username="quant@example.com", password="StrongPassword123!")
        from dashboard.models import TradingStrategy, StrategyExecutionLog
        from dashboard.services.strategies import evaluate_trading_strategies

        # Создаем торговую стратегию:
        # BUY <= 130.0, SELL >= 170.0, начальный капитал 20000, объем 5 шт.
        strat = TradingStrategy.objects.create(
            user=self.user,
            name="Gazprom Swing",
            share=self.share,
            buy_threshold=130.0,
            sell_threshold=170.0,
            trade_quantity=5,
            initial_capital=20000.0,
            current_capital=20000.0,
        )

        # 1. Цена 145 - в коридоре, сделки нет
        evaluate_trading_strategies(self.share, 145.0)
        strat.refresh_from_db()
        self.assertEqual(strat.current_position_shares, 0)
        self.assertEqual(strat.current_capital, 20000.0)

        # 2. Цена упала до 125.0 <= 130.0 (Покупка 5 акций по 125 = 625.0)
        evaluate_trading_strategies(self.share, 125.0)
        strat.refresh_from_db()
        self.assertEqual(strat.current_position_shares, 5)
        self.assertEqual(strat.current_capital, 20000.0 - 625.0)
        self.assertEqual(strat.total_trades_count, 1)

        # 3. Цена выросла до 175.0 >= 170.0 (Продажа 5 акций по 175 = 875.0)
        evaluate_trading_strategies(self.share, 175.0)
        strat.refresh_from_db()
        self.assertEqual(strat.current_position_shares, 0)
        self.assertEqual(strat.current_capital, 19375.0 + 875.0) # 20250.0 (+250 RUB профита)
        self.assertEqual(strat.profit_loss, 250.0)
        self.assertEqual(strat.total_trades_count, 2)
        self.assertEqual(StrategyExecutionLog.objects.filter(strategy=strat).count(), 2)

