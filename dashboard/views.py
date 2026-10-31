from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from .forms import ShareModelForm, TradeForm, TradingStrategyForm, WatchlistForm
from .models import (
    PriceHistory,
    PortfolioTransaction,
    Share,
    StrategyLog,
    TradingStrategy,
    UserNotification,
    WatchlistItem,
)
from .services.graph import get_graph
from .services.portfolio import (
    calculate_portfolio_summary,
    execute_trade,
    get_or_create_portfolio,
)
from .services.price_history import build_history_chart, get_price_statistics
from .tasks import process_share_price_update, update_last_price


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated

    def handle_no_permission(self):
        return redirect("user:auth")


# ==========================================
# 1. Каталог и базовые операции с акциями
# ==========================================


class ShareListView(ListView):
    """Список всех доступных акций с индикатором тренда"""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            ctx["unread_notifications_count"] = UserNotification.objects.filter(
                user=self.request.user, is_read=False
            ).count()
        return ctx


class ShareDetailView(View):
    """Детальная информация об акции, график Tinkoff/эмулятора + ссылка на историю цен"""

    @staticmethod
    def get(request, pk):
        share = get_object_or_404(Share, id=pk)
        stats = get_price_statistics(share, days=30)
        return render(
            request,
            "dashboard/detail.html",
            {
                "share": share,
                "plot_div": get_graph(share),
                "stats": stats,
            },
        )


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление инструмента"""

    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.last_price is not None:
            process_share_price_update(
                self.object, self.object.last_price, source="manual"
            )
        messages.success(self.request, f"Акция {self.object.ticker} успешно создана.")
        return response


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Редактирование инструмента (с возможностью ручного изменения цены)"""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        old_price = self.get_object().last_price
        response = super().form_valid(form)
        new_price = self.object.last_price
        if new_price is not None and new_price != old_price:
            process_share_price_update(self.object, new_price, source="manual")
            messages.success(
                self.request,
                f"Цена {self.object.ticker} обновлена до {new_price} {self.object.currency}. История цен зафиксирована, алерты и стратегии проверены.",
            )
        else:
            messages.success(self.request, f"Данные акции {self.object.ticker} обновлены.")
        return response


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление акции"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")


class SimulateMarketTickView(IsUserAuthenticatedMixin, View):
    """Смоделировать рыночные торги: запускает шаг обновления цен для всех акций"""

    def post(self, request):
        update_last_price()
        messages.success(
            request,
            "Рыночные котировки успешно обновлены! История цен сохранена, алерты и торговые стратегии проверены.",
        )
        return redirect(request.META.get("HTTP_REFERER", "dashboard:index"))


# ==========================================
# 2. Персональный мониторинг акций (Watchlist)
# ==========================================


class WatchlistView(IsUserAuthenticatedMixin, View):
    """Страница наблюдения за акциями и управление ценовыми алертами"""

    def get(self, request):
        watchlist = WatchlistItem.objects.filter(user=request.user).select_related("share")
        form = WatchlistForm()
        return render(
            request,
            "dashboard/watchlist.html",
            {"watchlist": watchlist, "form": form},
        )

    def post(self, request):
        form = WatchlistForm(request.POST)
        if form.is_valid():
            share = form.cleaned_data["share"]
            item, created = WatchlistItem.objects.get_or_create(
                user=request.user,
                share=share,
                defaults={
                    "target_price_low": form.cleaned_data.get("target_price_low"),
                    "target_price_high": form.cleaned_data.get("target_price_high"),
                },
            )
            if not created:
                item.target_price_low = form.cleaned_data.get("target_price_low")
                item.target_price_high = form.cleaned_data.get("target_price_high")
                item.save()
                messages.success(
                    request, f"Целевые уровни для {share.ticker} успешно обновлены."
                )
            else:
                messages.success(
                    request, f"Акция {share.ticker} добавлена в список наблюдения."
                )
        return redirect("dashboard:watchlist")


class WatchlistDeleteView(IsUserAuthenticatedMixin, View):
    """Удаление акции из списка наблюдения"""

    def post(self, request, pk):
        item = get_object_or_404(WatchlistItem, id=pk, user=request.user)
        ticker = item.share.ticker
        item.delete()
        messages.info(request, f"Акция {ticker} удалена из списка наблюдения.")
        return redirect("dashboard:watchlist")


class NotificationsView(IsUserAuthenticatedMixin, View):
    """Список уведомлений пользователя (срабатывание алертов и стратегий)"""

    def get(self, request):
        notifications = UserNotification.objects.filter(user=request.user).select_related(
            "share"
        )
        # Отмечаем как прочитанные
        notifications.filter(is_read=False).update(is_read=True)
        return render(
            request,
            "dashboard/notifications.html",
            {"notifications": notifications},
        )


# ==========================================
# 3. Виртуальный инвестиционный портфель
# ==========================================


class PortfolioView(IsUserAuthenticatedMixin, View):
    """Главный экран инвестиционного портфеля: баланс, открытые позиции, PnL"""

    def get(self, request):
        portfolio = get_or_create_portfolio(request.user)
        summary = calculate_portfolio_summary(portfolio)
        trade_form = TradeForm()
        shares = Share.objects.filter(last_price__isnull=False).order_by("ticker")
        return render(
            request,
            "dashboard/portfolio.html",
            {
                "portfolio": portfolio,
                "summary": summary,
                "trade_form": trade_form,
                "shares": shares,
            },
        )


class PortfolioTradeExecuteView(IsUserAuthenticatedMixin, View):
    """Исполнение виртуальной сделки покупки/продажи в портфеле"""

    def post(self, request):
        form = TradeForm(request.POST)
        if form.is_valid():
            share_id = form.cleaned_data["share_id"]
            action = form.cleaned_data["action"]
            quantity = form.cleaned_data["quantity"]

            share = get_object_or_404(Share, id=share_id)
            success, msg = execute_trade(
                user=request.user, share=share, action=action, quantity=quantity
            )

            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
        else:
            messages.error(request, "Некорректные параметры торговой операции.")

        return redirect("dashboard:portfolio")


class PortfolioTransactionsView(IsUserAuthenticatedMixin, ListView):
    """Журнал операций (история сделок купли/продажи)"""

    model = PortfolioTransaction
    template_name = "dashboard/transactions.html"
    paginate_by = 50
    context_object_name = "transactions"

    def get_queryset(self):
        portfolio = get_or_create_portfolio(self.request.user)
        return portfolio.transactions.select_related("share").order_by("-created_at")


# ==========================================
# 4. История изменения рыночных цен
# ==========================================


class PriceHistoryDetailView(View):
    """Просмотр накопленной истории изменения цен, расчет динамики и график БД"""

    def get(self, request, pk):
        share = get_object_or_404(Share, id=pk)
        days = int(request.GET.get("days", 30))
        stats = get_price_statistics(share, days=days)
        history_chart = build_history_chart(share)
        recent_records = PriceHistory.objects.filter(share=share).order_by("-created_at")[
            :50
        ]

        return render(
            request,
            "dashboard/price_history.html",
            {
                "share": share,
                "stats": stats,
                "history_chart": history_chart,
                "recent_records": recent_records,
                "selected_days": days,
            },
        )


# ==========================================
# 5. Симулятор инвестиционных стратегий
# ==========================================


class TradingStrategiesView(IsUserAuthenticatedMixin, View):
    """Управление торговыми роботами/стратегиями и просмотр логов их работы"""

    def get(self, request):
        strategies = TradingStrategy.objects.filter(user=request.user).select_related(
            "share"
        )
        logs = StrategyLog.objects.filter(strategy__user=request.user).select_related(
            "strategy", "strategy__share"
        )[:30]
        form = TradingStrategyForm()
        return render(
            request,
            "dashboard/strategies.html",
            {
                "strategies": strategies,
                "logs": logs,
                "form": form,
            },
        )

    def post(self, request):
        form = TradingStrategyForm(request.POST)
        if form.is_valid():
            strategy = form.save(commit=False)
            strategy.user = request.user
            strategy.save()
            messages.success(
                request, f"Стратегия '{strategy.name}' успешно создана и активирована."
            )
            return redirect("dashboard:strategies")

        strategies = TradingStrategy.objects.filter(user=request.user).select_related(
            "share"
        )
        logs = StrategyLog.objects.filter(strategy__user=request.user).select_related(
            "strategy", "strategy__share"
        )[:30]
        return render(
            request,
            "dashboard/strategies.html",
            {
                "strategies": strategies,
                "logs": logs,
                "form": form,
            },
        )


class StrategyToggleView(IsUserAuthenticatedMixin, View):
    """Включение/выключение стратегии"""

    def post(self, request, pk):
        strategy = get_object_or_404(TradingStrategy, id=pk, user=request.user)
        strategy.is_active = not strategy.is_active
        strategy.save(update_fields=["is_active"])
        status = "активирована" if strategy.is_active else "приостановлена"
        messages.info(request, f"Стратегия '{strategy.name}' {status}.")
        return redirect("dashboard:strategies")


class StrategyDeleteView(IsUserAuthenticatedMixin, View):
    """Удаление торговой стратегии"""

    def post(self, request, pk):
        strategy = get_object_or_404(TradingStrategy, id=pk, user=request.user)
        name = strategy.name
        strategy.delete()
        messages.info(request, f"Стратегия '{name}' удалена.")
        return redirect("dashboard:strategies")
