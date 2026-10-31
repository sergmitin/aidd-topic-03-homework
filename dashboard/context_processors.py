def unread_notifications(request):
    """Контекстный процессор для отображения количества непрочитанных уведомлений на иконке колокольчика"""
    if getattr(request, "user", None) and request.user.is_authenticated:
        from dashboard.models import UserNotification
        count = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return {"unread_notifications_count": count}
    return {"unread_notifications_count": 0}
