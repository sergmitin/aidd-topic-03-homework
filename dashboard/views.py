from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from .forms import ShareModelForm
from .models import (
    Portfolio,
    PortfolioPosition,
    PortfolioTransaction,
    PriceAlert,
    Share,
    StrategyExecutionLog,
    TradingStrategy,
    UserNotification,
    WatchlistItem,
)
from .services.alerts import create_price_alert, toggle_watchlist
from .services.graph import get_graph
from .services.portfolio import buy_share, get_or_create_portfolio, sell_share
from .services.price_history import build_history_chart, get_price_analytics, record_price_and_trigger_events
from .services.strategies import evaluate_strategies_for_share


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated

    @staticmethod
    def handle_no_permission():
        return redirect("dashboard:index")


# ==========================================
# Базовые представления каталога акций
# ==========================================

class ShareListView(ListView):
    """Список акций"""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            watchlist_ids = set(
                WatchlistItem.objects.filter(user=self.request.user).values_list(
                    "share_id", flat=True
                )
            )
            context["watchlist_ids"] = watchlist_ids
            context["unread_notifications_count"] = UserNotification.objects.filter(
                user=self.request.user, is_read=False
            ).count()
        return context


class ShareDetailView(View):
    """Детальная информация об акции и график"""

    @staticmethod
    def get(request, pk):
        share = get_object_or_404(Share, id=pk)
        return render(
            request,
            "dashboard/detail.html",
            {"plot_div": get_graph(share), "share": share},
        )


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление инструмента"""

    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.last_price:
            record_price_and_trigger_events(self.object, self.object.last_price)
        return response


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Редактирование инструмента"""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        old_price = self.get_object().last_price
        response = super().form_valid(form)
        if self.object.last_price and self.object.last_price != old_price:
            record_price_and_trigger_events(self.object, self.object.last_price)
        return response


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление инструмента"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")


# ==========================================
# Модуль 1: Персональный мониторинг и алерты
# ==========================================

class WatchlistView(LoginRequiredMixin, View):
    """Список наблюдения и управление ценовыми уровнями"""

    def get(self, request):
        watchlist = WatchlistItem.objects.filter(user=request.user).select_related("share")
        alerts = PriceAlert.objects.filter(user=request.user).select_related("share")
        notifications = UserNotification.objects.filter(user=request.user)
        all_shares = Share.objects.all().order_by("name")

        return render(
            request,
            "dashboard/watchlist.html",
            {
                "watchlist": watchlist,
                "alerts": alerts,
                "notifications": notifications,
                "all_shares": all_shares,
            },
        )


class ToggleWatchlistView(LoginRequiredMixin, View):
    """Добавление/удаление акции из списка наблюдения"""

    def post(self, request, share_id):
        is_added, share = toggle_watchlist(request.user, share_id)
        if is_added:
            messages.success(request, f"Акция {share.ticker} добавлена в список наблюдения.")
        else:
            messages.info(request, f"Акция {share.ticker} удалена из списка наблюдения.")
        return redirect(request.META.get("HTTP_REFERER", "dashboard:index"))


class CreateAlertView(LoginRequiredMixin, View):
    """Создание целевого ценового уровня (алерта)"""

    def post(self, request):
        share_id = request.POST.get("share_id")
        target_price = request.POST.get("target_price")
        condition = request.POST.get("condition", "above")

        if not share_id or not target_price:
            messages.error(request, "Заполните все поля для создания уведомления.")
            return redirect("dashboard:watchlist")

        try:
            target_price_float = float(target_price)
            alert = create_price_alert(
                request.user, share_id, target_price_float, condition
            )
            messages.success(
                request,
                f"Ценовой уровень для {alert.share.ticker} ({alert.get_condition_display()} {target_price_float}) успешно установлен.",
            )
        except Exception as e:
            messages.error(request, f"Ошибка создания уведомления: {e}")

        return redirect("dashboard:watchlist")


class DeleteAlertView(LoginRequiredMixin, View):
    """Удаление ценового алерта"""

    def post(self, request, alert_id):
        alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
        ticker = alert.share.ticker
        alert.delete()
        messages.info(request, f"Уведомление для {ticker} удалено.")
        return redirect("dashboard:watchlist")


class NotificationsView(LoginRequiredMixin, View):
    """Просмотр и отметка прочитанными уведомлений"""

    def get(self, request):
        notifications = UserNotification.objects.filter(user=request.user)
        # Отмечаем прочитанными при открытии
        notifications.filter(is_read=False).update(is_read=True)
        return render(
            request, "dashboard/notifications.html", {"notifications": notifications}
        )


# ==========================================
# Модуль 2: Виртуальный инвестиционный портфель
# ==========================================

class PortfolioView(LoginRequiredMixin, View):
    """Главная страница виртуального портфеля"""

    def get(self, request):
        portfolio = get_or_create_portfolio(request.user)
        positions = portfolio.positions.all().select_related("share")
        transactions = portfolio.transactions.all().select_related("share")[:10]
        shares = Share.objects.all().order_by("name")

        return render(
            request,
            "dashboard/portfolio.html",
            {
                "portfolio": portfolio,
                "positions": positions,
                "transactions": transactions,
                "shares": shares,
            },
        )


class BuyShareView(LoginRequiredMixin, View):
    """Операция виртуальной покупки акции"""

    def post(self, request):
        share_id = request.POST.get("share_id")
        quantity_str = request.POST.get("quantity", "1")

        try:
            quantity = int(quantity_str)
        except ValueError:
            messages.error(request, "Укажите корректное количество акций.")
            return redirect("dashboard:portfolio")

        success, message = buy_share(request.user, share_id, quantity)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect("dashboard:portfolio")


class SellShareView(LoginRequiredMixin, View):
    """Операция виртуальной продажи акции"""

    def post(self, request):
        share_id = request.POST.get("share_id")
        quantity_str = request.POST.get("quantity", "1")

        try:
            quantity = int(quantity_str)
        except ValueError:
            messages.error(request, "Укажите корректное количество акций.")
            return redirect("dashboard:portfolio")

        success, message = sell_share(request.user, share_id, quantity)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect("dashboard:portfolio")


class TransactionHistoryView(LoginRequiredMixin, ListView):
    """История операций с ценными бумагами"""

    model = PortfolioTransaction
    template_name = "dashboard/transactions.html"
    context_object_name = "transactions"
    paginate_by = 25

    def get_queryset(self):
        portfolio = get_or_create_portfolio(self.request.user)
        return portfolio.transactions.all().select_related("share")


# ==========================================
# Модуль 3: История цен и аналитика
# ==========================================

class PriceHistoryAnalyticsView(View):
    """Просмотр истории изменения рыночных цен и аналитики"""

    def get(self, request, share_id):
        share = get_object_or_404(Share, id=share_id)
        period = request.GET.get("period", "1m")
        analytics = get_price_analytics(share, period=period)
        chart_div = build_history_chart(share, period=period)
        all_shares = Share.objects.all().order_by("name")

        return render(
            request,
            "dashboard/price_history.html",
            {
                "share": share,
                "period": period,
                "analytics": analytics,
                "chart_div": chart_div,
                "all_shares": all_shares,
            },
        )


class SimulatePriceTickView(LoginRequiredMixin, View):
    """Симуляция нового ценового тика для интерактивной демонстрации аналитики и алертов"""

    def post(self, request, share_id):
        share = get_object_or_404(Share, id=share_id)
        new_price_str = request.POST.get("new_price")

        try:
            new_price = float(new_price_str)
        except (TypeError, ValueError):
            # Если цена не указана, моделируем небольшое изменение +/- 2%
            current = share.last_price or 100.0
            import random
            delta = current * random.choice([-0.03, -0.015, 0.015, 0.035])
            new_price = round(current + delta, 2)

        old_price = share.last_price
        share.last_price = new_price
        if old_price is not None:
            share.is_trend_high = bool(new_price >= old_price)
        share.updated_at = timezone.now()
        share.save()

        # Фиксируем в историю и запускаем проверки алертов и стратегий
        record_price_and_trigger_events(share, new_price)

        messages.success(
            request,
            f"Зафиксирована новая цена для {share.ticker}: {new_price} {share.currency}. История обновлена.",
        )
        return redirect(f"{reverse('dashboard:price_history', kwargs={'share_id': share.id})}?period={request.POST.get('period', '1m')}")


# ==========================================
# Модуль 4: Симулятор инвестиционных стратегий
# ==========================================

class StrategiesListView(LoginRequiredMixin, View):
    """Список инвестиционных стратегий пользователя и создание новой"""

    def get(self, request):
        strategies = TradingStrategy.objects.filter(user=request.user).select_related("share")
        shares = Share.objects.all().order_by("name")
        recent_logs = StrategyExecutionLog.objects.filter(
            strategy__user=request.user
        ).select_related("strategy", "strategy__share")[:15]

        return render(
            request,
            "dashboard/strategies.html",
            {
                "strategies": strategies,
                "shares": shares,
                "recent_logs": recent_logs,
            },
        )

    def post(self, request):
        name = request.POST.get("name")
        share_id = request.POST.get("share_id")
        buy_threshold = request.POST.get("buy_threshold")
        sell_threshold = request.POST.get("sell_threshold")
        trade_quantity = request.POST.get("trade_quantity", "1")
        initial_capital = request.POST.get("initial_capital", "50000")

        try:
            share = Share.objects.get(id=share_id)
            buy_val = float(buy_threshold)
            sell_val = float(sell_threshold)
            qty_val = int(trade_quantity)
            cap_val = float(initial_capital)

            if buy_val >= sell_val:
                messages.error(request, "Порог покупки должен быть строго ниже порога продажи.")
                return redirect("dashboard:strategies")

            strat = TradingStrategy.objects.create(
                user=request.user,
                name=name or f"Стратегия {share.ticker}",
                share=share,
                buy_threshold=buy_val,
                sell_threshold=sell_val,
                trade_quantity=qty_val,
                initial_capital=cap_val,
                current_capital=cap_val,
            )
            # Сразу проверяем текущую цену акции при создании стратегии
            if share.last_price:
                evaluate_trading_strategies(share, share.last_price)
            messages.success(request, f"Стратегия '{strat.name}' успешно создана и активирована.")
        except Exception as e:
            messages.error(request, f"Ошибка создания стратегии: {e}")

        return redirect("dashboard:strategies")


class StrategyDetailView(LoginRequiredMixin, View):
    """Детали стратегии и журнал исполнения сделок"""

    def get(self, request, strategy_id):
        strategy = get_object_or_404(TradingStrategy, id=strategy_id, user=request.user)
        logs = strategy.execution_logs.all()

        return render(
            request,
            "dashboard/strategy_detail.html",
            {"strategy": strategy, "logs": logs},
        )


class StrategyToggleView(LoginRequiredMixin, View):
    """Включение / пауза стратегии"""

    def post(self, request, strategy_id):
        strategy = get_object_or_404(TradingStrategy, id=strategy_id, user=request.user)
        strategy.is_active = not strategy.is_active
        strategy.save()
        status_text = "активирована" if strategy.is_active else "поставлена на паузу"
        messages.info(request, f"Стратегия '{strategy.name}' {status_text}.")
        return redirect("dashboard:strategies")


class StrategyDeleteView(LoginRequiredMixin, View):
    """Удаление стратегии"""

    def post(self, request, strategy_id):
        strategy = get_object_or_404(TradingStrategy, id=strategy_id, user=request.user)
        name = strategy.name
        strategy.delete()
        messages.info(request, f"Стратегия '{name}' удалена.")
        return redirect("dashboard:strategies")


class LoadDemoSharesView(View):
    """Инициализация стартового каталога акций одной кнопкой из веб-интерфейса"""

    def post(self, request):
        from django.core.management import call_command
        call_command("add_shares")
        messages.success(request, "Стартовый каталог демонстрационных акций успешно загружен.")
        return redirect("dashboard:index")

