from django import forms

from .models import Share


class ShareModelForm(forms.ModelForm):
    """Инструмент"""

    class Meta:
        model = Share
        # last_price, is_trend_high, updated_at управляются системой автоматически
        fields = ["figi", "isin", "name", "ticker", "currency", "uid"]
