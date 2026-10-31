"""
Management-команда для наполнения базы тестовыми данными акций.
Используется для разработки и тестирования без Tinkoff API токена.
"""
from django.core.management.base import BaseCommand

from dashboard.models import Share

SAMPLE_SHARES = [
    {
        "figi": "BBG004730N88",
        "isin": "RU0009029540",
        "name": "Сбербанк",
        "ticker": "SBER",
        "currency": "rub",
        "uid": "a92d4fc7-edd6-4dee-bbd5-02c04a5c1a5e",
        "last_price": 278.5,
        "is_trend_high": True,
    },
    {
        "figi": "BBG004731354",
        "isin": "RU0007661625",
        "name": "Газпром",
        "ticker": "GAZP",
        "currency": "rub",
        "uid": "7706aa38-57b4-4c66-8d08-10ab870a9e12",
        "last_price": 163.2,
        "is_trend_high": False,
    },
    {
        "figi": "BBG004S68473",
        "isin": "RU000A0JP5V6",
        "name": "Лукойл",
        "ticker": "LKOH",
        "currency": "rub",
        "uid": "4f96da08-9de3-4e75-8a5a-4a3f68db7e26",
        "last_price": 6820.0,
        "is_trend_high": True,
    },
    {
        "figi": "BBG006L8G4H1",
        "isin": "RU000A0JX0J2",
        "name": "Яндекс",
        "ticker": "YNDX",
        "currency": "rub",
        "uid": "10e17a87-3bce-4a1f-9dfc-720396f98a3c",
        "last_price": 3890.0,
        "is_trend_high": True,
    },
    {
        "figi": "BBG004731489",
        "isin": "RU0009062467",
        "name": "Роснефть",
        "ticker": "ROSN",
        "currency": "rub",
        "uid": "b5b1c1a0-95c3-4a91-93b2-1ef7462cfa91",
        "last_price": 512.8,
        "is_trend_high": False,
    },
    {
        "figi": "BBG004RVFCY3",
        "isin": "RU000A0JKQU8",
        "name": "Норникель",
        "ticker": "GMKN",
        "currency": "rub",
        "uid": "e4faeadb-28c8-4f82-967d-735e25b1fd26",
        "last_price": 14320.0,
        "is_trend_high": True,
    },
    {
        "figi": "BBG004S681W1",
        "isin": "RU0009024629",
        "name": "ВТБ",
        "ticker": "VTBR",
        "currency": "rub",
        "uid": "d1c28c91-7ae1-43bb-a7a1-4c5c0eab5218",
        "last_price": 0.023,
        "is_trend_high": False,
    },
    {
        "figi": "BBG00475KHX6",
        "isin": "RU0007252813",
        "name": "Магнит",
        "ticker": "MGNT",
        "currency": "rub",
        "uid": "8a4b5c6d-7e8f-9012-abcd-ef1234567890",
        "last_price": 5200.0,
        "is_trend_high": True,
    },
]


class Command(BaseCommand):
    help = "Populate database with sample shares for development/testing (no Tinkoff token required)"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for data in SAMPLE_SHARES:
            _, created = Share.objects.update_or_create(
                figi=data["figi"],
                defaults=data,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {created_count} created, {updated_count} updated."
            )
        )
