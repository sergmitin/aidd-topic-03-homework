# TASK3_MODERNIZATION.md — Модернизация, устранение дефектов и рефакторинг

## Обновление зависимостей

| Библиотека | Было | Стало |
|---|---|---|
| Django | 4.1.7 | 4.2.16 (LTS) |
| celery | 5.2.7 | 5.4.0 |
| redis | 4.5.1 | 5.2.0 |
| djangorestframework | 3.14.0 | 3.15.2 |
| django-filter | 22.1 | 24.3 |
| plotly | 5.13.1 | 5.24.1 |
| psycopg2-binary | 2.9.5 | 2.9.10 |
| crispy-bootstrap3 | 2022.1 | 2024.1 |
| django-crispy-forms | 2.0 | 2.3 |
| protobuf | 3.20.3 | 4.25.5 |
| grpcio | 1.51.3 | 1.67.1 |
| pydantic | 1.10.6 | 1.10.21 |
| tenacity | 8.2.2 | 9.0.0 |

**Удалены** из `requirements.txt` инструменты разработки, не относящиеся к runtime: `black`, `isort`, `mypy-extensions`, `pathspec`, `platformdirs`, `tomli` (эти пакеты должны быть в dev-зависимостях, отдельно от prod).

---

## Устранённые дефекты

### Д-01. `SECRET_KEY` и `TINKOFF_TOKEN` захардкожены в коде
**Файл:** `config/settings.py`  
**Проблема:** Секретные значения хранились как пустые строки прямо в коде — критическая угроза безопасности.  
**Исправление:** Все секреты и настройки окружения теперь читаются из переменных окружения через `os.environ.get()` с безопасными fallback-значениями для разработки. То же сделано для `ALLOWED_HOSTS`, настроек БД и `CELERY_BROKER_URL`.

### Д-02. `logger` объявлен в `settings.py`
**Файл:** `config/settings.py`  
**Проблема:** `logger = logging.getLogger("main")` в модуле настроек — антипаттерн. Модуль конфигурации не должен содержать логгеры.  
**Исправление:** Строка удалена из `settings.py`. Логгер объявляется в каждом модуле, который его использует (`tasks.py`, `market_data.py`).

### Д-03. REST API не требовал аутентификации
**Файл:** `config/settings.py`  
**Проблема:** Все методы `ShareViewSet` (в т.ч. POST, PUT, DELETE) были доступны анонимным пользователям.  
**Исправление:** В `REST_FRAMEWORK` добавлены `DEFAULT_AUTHENTICATION_CLASSES` (SessionAuthentication) и `DEFAULT_PERMISSION_CLASSES` (IsAuthenticatedOrReadOnly). Теперь изменяющие операции требуют авторизации.

### Д-04. Редирект при отказе в доступе вёл на главную страницу
**Файл:** `dashboard/views.py`  
**Проблема:** `IsUserAuthenticatedMixin.handle_no_permission()` редиректил на `dashboard:index` вместо страницы логина.  
**Исправление:** Изменён редирект на `user:auth`.

### Д-05. `ShareDetailView` выбрасывал 500 при несуществующем объекте
**Файл:** `dashboard/views.py`  
**Проблема:** `Share.objects.get(id=pk)` выбрасывал `DoesNotExist` при несуществующем pk, что приводило к ошибке 500.  
**Исправление:** Заменено на `get_object_or_404(Share, id=pk)`.

### Д-06. `updated_at` не обновлялся при фоновом обновлении цены
**Файл:** `dashboard/tasks.py`  
**Проблема:** Поле `updated_at` с `auto_now=True` не обновляется при вызове `.update()` — только при `.save()`. В результате время обновления цены в БД не фиксировалось корректно.  
**Исправление:** Обновление переписано через `.save(update_fields=[...])`, что корректно обновляет `auto_now` поле.

### Д-07. Некорректная логика тренда при первом обновлении
**Файл:** `dashboard/tasks.py`  
**Проблема:** Если `share.last_price` равен `None` (первое обновление), сравнение `share.last_price > last_price` выбрасывало исключение. Блок `except` устанавливал `is_trend_high = True`, что является некорректным значением.  
**Исправление:** Логика вынесена в функцию `calculate_trend()` в `price_utils.py`, которая возвращает `None` при отсутствии предыдущей цены.

### Д-08. Потеря дробной части цены
**Файлы:** `dashboard/services/market_data.py`, `dashboard/services/graph.py`  
**Проблема:** Цена Tinkoff API состоит из `units` (целые) и `nano` (миллиардные доли). В коде использовался только `units`, что давало неточные целые цены.  
**Исправление:** Создана утилита `quotation_to_float()` в `price_utils.py`, конвертирующая Quotation в `float` с учётом обеих частей. Используется в обоих сервисах.

### Д-09. `get_or_create` с несколькими полями в `add_shares`
**Файл:** `dashboard/management/commands/add_shares.py`  
**Проблема:** При изменении атрибутов инструмента на стороне Tinkoff API (например, `name`) повторный запуск команды создавал дубликат вместо обновления.  
**Исправление:** Заменено на `update_or_create` с поиском по уникальному `figi` и обновлением остальных полей.

### Д-10. Несоответствие названия Celery-задачи
**Файл:** `config/celery.py`  
**Проблема:** Задача называлась `"add-every-5-min"`, но выполнялась каждые 10 секунд.  
**Исправление:** Переименована в `"update-last-price-every-10-sec"`.

### Д-11. `fields = "__all__"` в форме акции
**Файл:** `dashboard/forms.py`  
**Проблема:** Форма открывала для ручного редактирования поля `last_price`, `is_trend_high`, `updated_at`, которые должны управляться только системой.  
**Исправление:** Заменено на явный список редактируемых полей: `["figi", "isin", "name", "ticker", "currency", "uid"]`.

---

## Рефакторинг

### Р-01. Вынесена логика работы с ценами в отдельный модуль
**Создан:** `dashboard/services/price_utils.py`  
Содержит две функции:
- `calculate_trend(old_price, new_price)` — определение направления тренда
- `quotation_to_float(quotation)` — конвертация Tinkoff Quotation в float  

Устранено дублирование логики между `tasks.py`, `market_data.py` и `graph.py`.

### Р-02. Убран `import *` в router
**Файл:** `dashboard/api/v1/router.py`  
`from .views import *` заменено на `from .views import ShareViewSet`.

### Р-03. Переименована функция `get_last_data` → `get_last_price`
**Файл:** `dashboard/services/market_data.py`  
Старое название не отражало, что функция возвращает только цену. Переменная `detetime` (опечатка в оригинале) также устранена — дата из ответа API более не возвращается, так как не использовалась.

### Р-04. Исправлена опечатка в комментарии
**Файл:** `dashboard/views.py`  
Комментарий `"""Удаление задачи"""` в `ShareDeleteView` исправлен на `"""Удаление акции"""`.

### Р-06. Graceful degradation при отсутствии токена Tinkoff
**Файл:** `dashboard/services/graph.py`  
При пустом `TINKOFF_TOKEN` функция `get_graph()` возвращает HTML-заглушку вместо падения с исключением. Ошибки API также перехватываются и не крашат страницу.

### Р-07. Management-команда для тестовых данных
**Создан:** `dashboard/management/commands/add_sample_shares.py`  
Команда `python manage.py add_sample_shares` наполняет БД тестовым набором из 8 российских акций. Позволяет запустить и протестировать приложение без доступа к Tinkoff API.

