from django.core.management.base import BaseCommand

from config.settings import TINKOFF_TOKEN
from dashboard.models import Share


class Command(BaseCommand):
    help = "Add or update shares from Tinkoff Invest API (falls back to sample shares if no token)"

    def handle(self, *args, **options):
        if not TINKOFF_TOKEN:
            self.stdout.write(
                self.style.WARNING(
                    "TINKOFF_TOKEN не задан. Используйте команду 'add_sample_shares' для заполнения демо-данными."
                )
            )
            return

        try:
            from tinkoff.invest import Client

            with Client(TINKOFF_TOKEN) as client:
                shares = client.instruments.shares()
                for share in shares.instruments:
                    Share.objects.update_or_create(
                        figi=share.figi,
                        defaults={
                            "name": share.name,
                            "isin": share.isin,
                            "ticker": share.ticker,
                            "currency": share.currency,
                            "uid": share.uid,
                        },
                    )
            self.stdout.write(self.style.SUCCESS("Акции успешно загружены из Tinkoff API."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка при загрузке акций: {e}"))
