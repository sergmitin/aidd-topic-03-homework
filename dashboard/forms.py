import uuid
from django import forms
from .models import Share


class ShareModelForm(forms.ModelForm):
    """Форма создания и редактирования финансового инструмента"""

    figi = forms.CharField(
        label="FIGI (код финансового инструмента)",
        required=False,
        help_text="Необязательно. При отсутствии будет сгенерирован автоматически.",
        widget=forms.TextInput(attrs={"placeholder": "Например: BBG004730N88"}),
    )
    isin = forms.CharField(
        label="ISIN (международный код бумаги)",
        required=False,
        help_text="Необязательно. При отсутствии будет сгенерирован автоматически.",
        widget=forms.TextInput(attrs={"placeholder": "Например: RU0009029540"}),
    )
    name = forms.CharField(
        label="Наименование компании",
        widget=forms.TextInput(attrs={"placeholder": "Например: ПАО Сбербанк"}),
    )
    ticker = forms.CharField(
        label="Биржевой тикер",
        widget=forms.TextInput(attrs={"placeholder": "Например: SBER"}),
    )
    currency = forms.CharField(
        label="Валюта торгов (RUB, USD, EUR)",
        max_length=5,
        initial="RUB",
        widget=forms.TextInput(attrs={"placeholder": "RUB"}),
    )
    last_price = forms.FloatField(
        label="Текущая рыночная цена",
        initial=100.0,
        widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "100.00"}),
    )
    uid = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    is_trend_high = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Share
        fields = [
            "ticker",
            "name",
            "currency",
            "last_price",
            "isin",
            "figi",
            "uid",
            "is_trend_high",
        ]

    def clean(self):
        cleaned_data = super().clean()
        ticker = (cleaned_data.get("ticker") or "STOCK").upper()

        if not cleaned_data.get("figi"):
            cleaned_data["figi"] = f"BBG{ticker.ljust(9, 'X')[:9]}"

        if not cleaned_data.get("isin"):
            cleaned_data["isin"] = f"RU{ticker.ljust(10, '0')[:10]}"

        if not cleaned_data.get("uid"):
            cleaned_data["uid"] = str(uuid.uuid4())

        if cleaned_data.get("is_trend_high") is None:
            cleaned_data["is_trend_high"] = True

        if cleaned_data.get("currency"):
            cleaned_data["currency"] = cleaned_data["currency"].upper()[:3]

        return cleaned_data

