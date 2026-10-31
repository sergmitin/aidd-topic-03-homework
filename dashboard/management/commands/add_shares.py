from django.core.management.base import BaseCommand
from config.settings import TINKOFF_TOKEN
from dashboard.models import Share

DEMO_SHARES = [
    {
        "name": "Сбер Банк",
        "ticker": "SBER",
        "figi": "BBG004730N88",
        "isin": "RU0009029540",
        "currency": "RUB",
        "uid": "e6123145-9665-43e0-8413-cd61b8aa9b13",
        "last_price": 280.50,
        "is_trend_high": True,
    },
    {
        "name": "Газпром",
        "ticker": "GAZP",
        "figi": "BBG004730RP0",
        "isin": "RU0007661625",
        "currency": "RUB",
        "uid": "968c116d-bb92-4687-86e1-aecd1520e915",
        "last_price": 135.20,
        "is_trend_high": False,
    },
    {
        "name": "Яндекс",
        "ticker": "YDEX",
        "figi": "TCS00A107T19",
        "isin": "RU000A107T19",
        "currency": "RUB",
        "uid": "21727716-16e5-47ee-bbd3-6cb2309e3e3b",
        "last_price": 3950.00,
        "is_trend_high": True,
    },
    {
        "name": "Лукойл",
        "ticker": "LKOH",
        "figi": "BBG0044cd088",
        "isin": "RU0009024277",
        "currency": "RUB",
        "uid": "87123145-9665-43e0-8413-cd61b8aa9b22",
        "last_price": 6890.00,
        "is_trend_high": True,
    },
    {
        "name": "Apple Inc.",
        "ticker": "AAPL",
        "figi": "BBG000B9XRY4",
        "isin": "US0378331005",
        "currency": "USD",
        "uid": "a9eb4238-eba9-488c-b102-b6140fd08e38",
        "last_price": 225.40,
        "is_trend_high": True,
    },
]


class Command(BaseCommand):
    help = "Add shares to DB (Tinkoff API or built-in demo catalog)"

    def handle(self, *args, **options):
        imported_count = 0

        if TINKOFF_TOKEN:
            try:
                from tinkoff.invest import Client

                with Client(TINKOFF_TOKEN) as client:
                    shares = client.instruments.shares()
                    for share in shares.instruments:
                        _, created = Share.objects.get_or_create(
                            figi=share.figi,
                            defaults={
                                "name": share.name,
                                "isin": share.isin,
                                "ticker": share.ticker,
                                "currency": share.currency,
                                "uid": share.uid,
                            },
                        )
                        if created:
                            imported_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Успешно импортировано {imported_count} акций из Tinkoff Invest API."
                    )
                )
                return
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"Не удалось подключиться к Tinkoff API ({e}). Переход к демонстрационному набору."
                    )
                )

        # Fallback на встроенные демонстрационные акции
        for item in DEMO_SHARES:
            _, created = Share.objects.get_or_create(
                ticker=item["ticker"],
                defaults=item,
            )
            if created:
                imported_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Успешно инициализирована база данных ({imported_count} новых акций добавлено)."
            )
        )
