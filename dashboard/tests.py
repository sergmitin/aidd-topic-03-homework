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
