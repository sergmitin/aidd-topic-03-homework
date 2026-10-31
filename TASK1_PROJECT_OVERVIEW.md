# ANALYSIS.md — Анализ приложения Investing Demo

## 1. Назначение приложения и технологический стек

**Назначение:** Investing Demo — веб-приложение для мониторинга биржевых акций. Приложение загружает список инструментов с Tinkoff Invest API, хранит их в базе данных, периодически обновляет текущие рыночные цены и отображает графики изменения цен.

### Технологический стек

| Слой | Технологии |
|---|---|
| Backend-фреймворк | Django 4.1.7 |
| REST API | Django REST Framework 3.14.0 |
| Очереди задач | Celery 5.2.7 |
| Брокер сообщений | Redis |
| База данных | PostgreSQL (psycopg2-binary 2.9.5) |
| Внешний API | Tinkoff Invest API (tinkoff-investments 0.2.0b50) |
| Визуализация | Plotly 5.13.1 |
| UI-компоненты | Bootstrap 3, django-crispy-forms |
| Фильтрация API | django-filter 22.1 |
| Контейнеризация | Docker / docker-compose |

---

## 2. Структура проекта и назначение компонентов

```
aidd-topic-03-homework/
├── config/                    # Конфигурация проекта
│   ├── settings.py            # Настройки Django, Celery, БД, логирование
│   ├── celery.py              # Инициализация Celery и расписание задач
│   ├── urls.py                # Корневые URL-маршруты
│   ├── wsgi.py / asgi.py      # Точки входа WSGI/ASGI
│   └── __init__.py
│
├── dashboard/                 # Основное приложение (акции)
│   ├── models.py              # Модель Share (акция)
│   ├── views.py               # CBV: список, детали, создание, редактирование, удаление
│   ├── forms.py               # ShareModelForm
│   ├── urls.py                # URL-маршруты dashboard
│   ├── admin.py               # Регистрация модели в Django Admin
│   ├── tasks.py               # Celery-задача update_last_price
│   ├── services/
│   │   ├── market_data.py     # Получение последней цены через Tinkoff API
│   │   └── graph.py           # Построение графика свечей через Tinkoff API + Plotly
│   ├── api/
│   │   └── v1/
│   │       ├── views.py       # ShareViewSet (ModelViewSet)
│   │       ├── serializer.py  # ShareSerializer
│   │       ├── router.py      # DRF Router, регистрация /shares/
│   │       └── urls.py        # Подключение router.urls
│   ├── management/
│   │   └── commands/
│   │       └── add_shares.py  # Management-команда: загрузка акций из Tinkoff API
│   ├── migrations/            # 7 миграций (0001–0007)
│   └── templates/dashboard/   # HTML-шаблоны (list, detail, create, delete, base)
│
├── user/                      # Приложение аутентификации
│   ├── models.py              # Алиас стандартной модели User (get_user_model)
│   ├── views.py               # AuthView, RegistrationView, LogoutView
│   ├── forms.py               # AuthForm, RegistrationForm
│   ├── urls.py                # /user/login/, /user/registration/, /user/logout/
│   └── templates/user/        # HTML-шаблоны (auth, registration, base)
│
├── docker-compose.yml         # Запуск PostgreSQL в контейнере
├── requirements.txt           # Зависимости Python
├── manage.py
└── app.logs                   # Файл логов приложения
```

---

## 3. Архитектура приложения и взаимодействие компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│                        Клиентский браузер                        │
└───────┬──────────────────────────────────────┬──────────────────┘
        │  HTTP (Web UI)                        │  HTTP (REST API)
        ▼                                       ▼
┌───────────────────┐                 ┌─────────────────────────┐
│   Django Views    │                 │   Django REST Framework  │
│  (dashboard/      │                 │   ShareViewSet           │
│   views.py)       │                 │   /api/v1/shares/        │
└───────┬───────────┘                 └──────────┬──────────────┘
        │                                        │
        ▼                                        ▼
┌───────────────────────────────────────────────────────────────┐
│                    Django ORM / PostgreSQL                      │
│                         (Share model)                           │
└──────────────────────────────┬────────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
        ▼                               ▼
┌───────────────────┐         ┌─────────────────────────┐
│  Celery Beat      │         │  Tinkoff Invest API      │
│  (каждые 10 сек)  │────────▶│  (market_data, candles)  │
│  update_last_price│         └─────────────────────────┘
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Redis (брокер)   │
└───────────────────┘
```

### Поток данных

1. **Начальная загрузка:** `python manage.py add_shares` → Tinkoff API → PostgreSQL (таблица `Share`).
2. **Периодическое обновление цен:** Celery Beat запускает `update_last_price` каждые 10 секунд → Tinkoff API → обновление полей `last_price`, `is_trend_high` в БД.
3. **Просмотр списка акций:** браузер → Django `ShareListView` → ORM → PostgreSQL → HTML-шаблон.
4. **Просмотр детальной страницы:** браузер → `ShareDetailView` → `get_graph()` → Tinkoff API (свечи за 180 дней) → Plotly → HTML.
5. **REST API:** внешний клиент → DRF `ShareViewSet` → ORM → JSON-ответ.

---

## 4. Используемые библиотеки и внешние зависимости

### Ключевые зависимости

| Библиотека | Версия | Назначение |
|---|---|---|
| Django | 4.1.7 | Основной веб-фреймворк |
| djangorestframework | 3.14.0 | REST API |
| celery | 5.2.7 | Асинхронные/периодические задачи |
| redis | 4.5.1 | Клиент Redis (брокер Celery) |
| tinkoff-investments | 0.2.0b50 | Python SDK для Tinkoff Invest API |
| plotly | 5.13.1 | Построение интерактивных графиков |
| psycopg2-binary | 2.9.5 | Адаптер PostgreSQL |
| django-crispy-forms | 2.0 | Стилизация форм |
| crispy-bootstrap3 | 2022.1 | Bootstrap 3-шаблон для crispy-forms |
| django-filter | 22.1 | Фильтрация в DRF |
| protobuf | 3.20.3 | Требуется для gRPC / Tinkoff API |
| grpcio | 1.51.3 | gRPC транспорт для Tinkoff API |
| pydantic | 1.10.6 | Валидация данных (используется tinkoff SDK) |

### Внешние зависимости инфраструктуры

- **PostgreSQL** — основное хранилище данных (запускается через Docker).
- **Redis** — брокер сообщений Celery.
- **Tinkoff Invest API** — источник рыночных данных (требует API-токен).

---

## 5. Модель данных

### Сущность `Share` (Акция)

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | BigAutoField | PK, auto | Первичный ключ |
| `figi` | CharField(255) | unique | Идентификатор FIGI инструмента |
| `isin` | CharField(255) | — | Международный код ценной бумаги |
| `name` | CharField(255) | — | Наименование компании |
| `ticker` | CharField(10) | unique | Биржевой тикер |
| `currency` | CharField(20) | — | Валюта торгов |
| `uid` | CharField(255) | unique | Уникальный идентификатор Tinkoff |
| `last_price` | FloatField | null, blank | Последняя рыночная цена |
| `is_trend_high` | BooleanField | null, blank | Флаг роста цены (True — растёт) |
| `updated_at` | DateTimeField | auto_now | Время последнего обновления |

### Сущность `User`

Приложение использует стандартную модель `django.contrib.auth.User` через алиас `get_user_model()`. Кастомная модель отсутствует — используется стандартная Django User.  
Аутентификация производится по полю `username`, которому при регистрации присваивается значение email.

### ER-диаграмма

```
┌──────────────────────────────┐     ┌───────────────────────────┐
│           Share              │     │           User             │
├──────────────────────────────┤     ├───────────────────────────┤
│ id (PK)                      │     │ id (PK)                    │
│ figi (unique)                │     │ username (= email)         │
│ isin                         │     │ email                      │
│ name                         │     │ password (hashed)          │
│ ticker (unique)              │     │ is_staff                   │
│ currency                     │     │ is_active                  │
│ uid (unique)                 │     └───────────────────────────┘
│ last_price (nullable)        │
│ is_trend_high (nullable)     │
│ updated_at                   │
└──────────────────────────────┘
```

> Между `Share` и `User` связей нет — данные об акциях общие для всех пользователей.

---

## 6. Механизмы обработки запросов и взаимодействия с БД

### Web UI (HTML-интерфейс)

| URL | View | Метод | Доступ | Действие |
|---|---|---|---|---|
| `/` | `ShareListView` | GET | Все | Список акций, пагинация 100/стр., сортировка по name |
| `/<pk>` | `ShareDetailView` | GET | Все | Детальная страница + график (Plotly) |
| `/create` | `ShareCreateView` | GET/POST | Только авторизованные | Создание акции через форму |
| `/update/<pk>` | `ShareUpdateView` | GET/POST | Только авторизованные | Редактирование акции |
| `/delete/<pk>` | `ShareDeleteView` | GET/POST | Только авторизованные | Удаление акции |
| `/user/login/` | `AuthView` | GET/POST | Все | Форма входа |
| `/user/registration/` | `RegistrationView` | GET/POST | Все | Форма регистрации |
| `/user/logout/` | `LogoutView` | GET | Все | Выход из системы |

### REST API

| URL | ViewSet | Методы | Описание |
|---|---|---|---|
| `/api/v1/shares/` | `ShareViewSet` | GET, POST | Список акций / создание |
| `/api/v1/shares/<id>/` | `ShareViewSet` | GET, PUT, PATCH, DELETE | Операции с одной акцией |

**Фильтрация:** по полям `name`, `ticker` (точное совпадение).  
**Поиск:** по `name` (regex-поиск через `$name`).  
**Сортировка:** по `name`, `ticker`.  
**Пагинация:** LimitOffset, по умолчанию 100 записей.

### Авторизация и управление доступом

- Используется стандартная Django-аутентификация (сессии).
- Создание, редактирование и удаление акций защищены миксином `IsUserAuthenticatedMixin` (`UserPassesTestMixin`).
- При отказе в доступе пользователь перенаправляется на главную страницу (`dashboard:index`), а не на страницу входа — это отклонение от стандартного поведения Django.
- REST API не имеет аутентификации — все операции (в т.ч. POST, PUT, DELETE) доступны без авторизации.

### Периодические задачи (Celery)

- **Задача:** `dashboard.tasks.update_last_price`
- **Расписание:** каждые **10 секунд** (в коде именуется `"add-every-5-min"` — несоответствие названия и поведения)
- **Логика:** для каждой акции запрашивает последнюю цену через Tinkoff API, определяет направление тренда (`is_trend_high`) и обновляет запись в БД.

### Взаимодействие с БД

- ORM Django: `Share.objects.all()`, `Share.objects.get(id=pk)`, `Share.objects.filter(id=share.id).update(...)`, `Share.objects.get_or_create(...)`.
- Транзакции не используются явно.
- Команда `add_shares` использует `get_or_create` для идемпотентной загрузки инструментов.
