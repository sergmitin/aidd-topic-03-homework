from django import forms

from .models import Share, TradingStrategy, WatchlistItem


class ShareModelForm(forms.ModelForm):
    """Форма добавления и редактирования инструмента (с возможностью ручной установки рыночной цены)"""

    class Meta:
        model = Share
        fields = ["figi", "isin", "name", "ticker", "currency", "uid", "last_price"]
        widgets = {
            "figi": forms.TextInput(attrs={"class": "form-control"}),
            "isin": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "ticker": forms.TextInput(attrs={"class": "form-control"}),
            "currency": forms.TextInput(attrs={"class": "form-control"}),
            "uid": forms.TextInput(attrs={"class": "form-control"}),
            "last_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Текущая цена акции (можно задать вручную)",
                }
            ),
        }


class WatchlistForm(forms.ModelForm):
    """Форма добавления акции в персональный список наблюдения и установки целевых цен"""

    class Meta:
        model = WatchlistItem
        fields = ["share", "target_price_low", "target_price_high"]
        widgets = {
            "share": forms.Select(attrs={"class": "form-select"}),
            "target_price_low": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Уведомить при падении ниже...",
                    "step": "0.01",
                }
            ),
            "target_price_high": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Уведомить при росте выше...",
                    "step": "0.01",
                }
            ),
        }


class TradeForm(forms.Form):
    """Форма совершения виртуальной сделки покупки/продажи в портфеле"""

    TRANSACTION_TYPES = (
        ("BUY", "Купить"),
        ("SELL", "Продать"),
    )

    share_id = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=TRANSACTION_TYPES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Операция",
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        label="Количество бумаг",
    )


class TradingStrategyForm(forms.ModelForm):
    """Форма создания автоматической торговой стратегии"""

    class Meta:
        model = TradingStrategy
        fields = [
            "name",
            "share",
            "buy_price",
            "sell_price",
            "trade_quantity",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Например: Покупка Сбера на просадке"}
            ),
            "share": forms.Select(attrs={"class": "form-select"}),
            "buy_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "placeholder": "Покупать по цене <="}
            ),
            "sell_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "placeholder": "Продавать по цене >="}
            ),
            "trade_quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "value": "1"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
