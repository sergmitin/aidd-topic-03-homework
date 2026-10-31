from django.urls import include, path

from dashboard.views import (
    BuyShareView,
    CreateAlertView,
    DeleteAlertView,
    LoadDemoSharesView,
    NotificationsView,
    PortfolioView,
    PriceHistoryAnalyticsView,
    SellShareView,
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
    SimulatePriceTickView,
    StrategiesListView,
    StrategyDeleteView,
    StrategyDetailView,
    StrategyToggleView,
    ToggleWatchlistView,
    TransactionHistoryView,
    WatchlistView,
)

app_name = "dashboard"

urlpatterns = [
    # Каталог акций
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>/", ShareDetailView.as_view(), name="detail"),
    path("create/", ShareCreateView.as_view(), name="create"),
    path("load-demo-shares/", LoadDemoSharesView.as_view(), name="load_demo_shares"),
    path("update/<int:pk>/", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>/", ShareDeleteView.as_view(), name="delete"),

    # Модуль 1: Мониторинг и алерты
    path("watchlist/", WatchlistView.as_view(), name="watchlist"),
    path("watchlist/toggle/<int:share_id>/", ToggleWatchlistView.as_view(), name="watchlist_toggle"),
    path("alerts/create/", CreateAlertView.as_view(), name="create_alert"),
    path("alerts/delete/<int:alert_id>/", DeleteAlertView.as_view(), name="delete_alert"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),

    # Модуль 2: Виртуальный портфель
    path("portfolio/", PortfolioView.as_view(), name="portfolio"),
    path("portfolio/buy/", BuyShareView.as_view(), name="portfolio_buy"),
    path("portfolio/sell/", SellShareView.as_view(), name="portfolio_sell"),
    path("portfolio/transactions/", TransactionHistoryView.as_view(), name="portfolio_transactions"),

    # Модуль 3: История цен и аналитика
    path("history/<int:share_id>/", PriceHistoryAnalyticsView.as_view(), name="price_history"),
    path("history/tick/<int:share_id>/", SimulatePriceTickView.as_view(), name="simulate_price_tick"),

    # Модуль 4: Симулятор стратегий
    path("strategies/", StrategiesListView.as_view(), name="strategies"),
    path("strategies/<int:strategy_id>/", StrategyDetailView.as_view(), name="strategy_detail"),
    path("strategies/toggle/<int:strategy_id>/", StrategyToggleView.as_view(), name="strategy_toggle"),
    path("strategies/delete/<int:strategy_id>/", StrategyDeleteView.as_view(), name="strategy_delete"),

    # REST API
    path("api/", include("dashboard.api.urls")),
]
