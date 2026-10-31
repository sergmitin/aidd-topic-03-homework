from django.urls import include, path

from dashboard.views import (
    NotificationsView,
    PortfolioTradeExecuteView,
    PortfolioTransactionsView,
    PortfolioView,
    PriceHistoryDetailView,
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
    SimulateMarketTickView,
    StrategyDeleteView,
    StrategyToggleView,
    TradingStrategiesView,
    WatchlistDeleteView,
    WatchlistView,
)

app_name = "dashboard"

urlpatterns = [
    # 1. Каталог акций
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>/", ShareDetailView.as_view(), name="detail"),
    path("create/", ShareCreateView.as_view(), name="create"),
    path("update/<int:pk>/", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>/", ShareDeleteView.as_view(), name="delete"),
    path("market/simulate-tick/", SimulateMarketTickView.as_view(), name="simulate_tick"),

    # 2. Персональный мониторинг (Watchlist и уведомления)
    path("watchlist/", WatchlistView.as_view(), name="watchlist"),
    path("watchlist/delete/<int:pk>/", WatchlistDeleteView.as_view(), name="watchlist_delete"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),

    # 3. Виртуальный инвестиционный портфель
    path("portfolio/", PortfolioView.as_view(), name="portfolio"),
    path("portfolio/trade/", PortfolioTradeExecuteView.as_view(), name="portfolio_trade"),
    path("portfolio/transactions/", PortfolioTransactionsView.as_view(), name="portfolio_transactions"),

    # 4. История изменения цен
    path("history/<int:pk>/", PriceHistoryDetailView.as_view(), name="price_history"),

    # 5. Симулятор инвестиционных стратегий
    path("strategies/", TradingStrategiesView.as_view(), name="strategies"),
    path("strategies/toggle/<int:pk>/", StrategyToggleView.as_view(), name="strategy_toggle"),
    path("strategies/delete/<int:pk>/", StrategyDeleteView.as_view(), name="strategy_delete"),

    # REST API
    path("api/", include("dashboard.api.urls")),
]
