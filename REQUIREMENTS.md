# Восстановление функциональных требований проекта Investing Demo

Настоящий документ подготовлен в рамках выполнения **Задания №2** программы домашнего задания. В документе зафиксированы функциональные возможности, сценарии использования, бизнес-правила и функциональные требования, восстановленные на основе строгого анализа исходного кода приложения **Investing Demo**.

> [!IMPORTANT]
> В соответствии с методикой обратной разработки (Reverse Engineering) и требованиями Задания №2, в документе зафиксирована **фактически реализованная функциональность** приложения (as-is), а не желаемое целевое состояние. Каждое требование и бизнес-правило подкреплено кликабельной относительной ссылкой на файл в репозитории и точной цитатой подтверждающего исходного кода. Выявленные ошибки и недоработки выделены в отдельный раздел и не рассматриваются как функциональные требования.

---

## 1. Основные функциональные возможности приложения

На основе анализа программного кода выделены следующие модули и функциональные возможности:

1. **Каталог финансовых инструментов (акций):**
   - Просмотр глобального списка акций в виде таблицы с постраничной навигацией (пагинацией) по 100 записей.
   - Сортировка списка акций по алфавиту (по наименованию компании).
   - Цветовая индикация рыночного тренда цены: зеленый фон при росте или равенстве цены, розовый — при снижении.

2. **Детальная информация и график котировок:**
   - Просмотр карточки акции с отображением тикера, наименования компании, текущей цены, валюты и времени последнего обновления.
   - Построение интерактивного линейного графика дневных котировок закрытия за предшествующие 180 дней на базе библиотеки Plotly.

3. **Администрирование инструментов (CRUD) через веб-интерфейс:**
   - Добавление новой акции в базу данных через экранную форму.
   - Редактирование всех атрибутов существующей акции.
   - Удаление акции с предварительным экраном подтверждения.
   - Ограничение доступа: операции добавления, изменения и удаления доступны только аутентифицированным пользователям.

4. **Программный интерфейс (REST API):**
   - Получение списка акций с поддержкой пагинации (`LimitOffsetPagination`).
   - Получение детальной информации по конкретной акции по первичному ключу (`id`).
   - Создание, полное обновление (`PUT`), частичное обновление (`PATCH`) и удаление (`DELETE`) акций в формате JSON.
   - Фильтрация по наименованию (`name`) и тикеру (`ticker`), regex-поиск по названию (`$name`), сортировка по полям `name` и `ticker`.

5. **Фоновый мониторинг и синхронизация котировок:**
   - Периодический запуск фоновой задачи с интервалом 10 секунд через Celery Beat.
   - Запрос текущих рыночных котировок из внешнего биржевого сервиса Tinkoff Invest API.
   - Автоматический пересчет статуса тренда (`is_trend_high`) и сохранение последней цены (`last_price`).

6. **Первоначальный импорт данных:**
   - Загрузка перечня доступных акций из Tinkoff Invest API в БД через Django management-команду `python manage.py add_shares`.

7. **Аутентификация пользователей:**
   - Регистрация нового аккаунта с валидацией совпадения паролей и уникальности email.
   - Вход в систему с проверкой учетных данных (логином выступает email).
   - Завершение пользовательского сеанса (Logout).

---

## 2. Основные сценарии взаимодействия пользователя (Use Cases)

### UC-1: Регистрация нового пользователя
- **Актор:** Неаутентифицированный пользователь.
- **Предусловие:** Пользователь открыл страницу регистрации.
- **Основной поток:**
  1. Пользователь вводит email, пароль и повтор пароля в форму.
  2. Пользователь отправляет форму (POST).
  3. Система проверяет совпадение паролей и отсутствие дубликата email в базе.
  4. При успешной проверке создается запись `User` (где `username = email`), и пользователь автоматически аутентифицируется в текущей сессии.
  5. Система перенаправляет пользователя на главную страницу каталога акций.
- **Альтернативный поток (ошибка валидации):**
  - Пароли не совпадают либо email уже занят: система повторно отображает форму регистрации с сообщением об ошибке.

### UC-2: Вход в систему (Аутентификация)
- **Актор:** Зарегистрированный пользователь.
- **Предусловие:** Пользователь открыл страницу входа.
- **Основной поток:**
  1. Пользователь вводит email и пароль.
  2. Пользователь нажимает кнопку «Войти» (POST).
  3. Система сверяет учетные данные с базой пользователей (`authenticate`).
  4. При совпадении создается авторизованная сессия, и происходит редирект на главную страницу.
- **Альтернативный поток (неверные данные):**
  - Пользователь не найден или пароль неверен: отображается сообщение «Неверный логин или пароль! Повторите попытку.».

### UC-3: Завершение сеанса (Выход)
- **Актор:** Аутентифицированный пользователь.
- **Основной поток:**
  1. Пользователь нажимает кнопку «Выход» в шапке сайта.
  2. Выполняется GET-запрос к маршруту выхода.
  3. Сессия пользователя аннулируется, происходит редирект на главную страницу в статусе гостя.

### UC-4: Просмотр каталога акций
- **Актор:** Любой пользователь (анонимный или аутентифицированный).
- **Основной поток:**
  1. Пользователь переходит на главную страницу `/`.
  2. Система запрашивает из БД список акций, отсортированный по наименованию компании, с пагинацией по 100 элементов.
  3. Пользователь видит таблицу с колонками: Тикер, Название, ISIN, Текущая цена (с валютой).
  4. Ячейка цены подсвечивается зеленым цветом, если `is_trend_high=True`, или розовым, если `is_trend_high=False`.
  5. Для аутентифицированного пользователя дополнительно отображаются кнопка «Добавить» и колонка «Управление» с кнопками «Редактировать» и «Удалить».
  6. Пользователь может переключаться между страницами списка с помощью пагинатора внизу таблицы.

### UC-5: Детальный просмотр инструмента и графика котировок
- **Актор:** Любой пользователь.
- **Основной поток:**
  1. Пользователь кликает по тикеру акции в таблице каталога.
  2. Система загружает данные акции из БД по первичному ключу (`pk`).
  3. Система обращается к внешнему Tinkoff API и запрашивает дневные свечи закрытия за последние 180 дней.
  4. Система строит линейный график Plotly и отображает страницу с параметрами акции и интерактивным графиком.

### UC-6: Добавление новой акции
- **Актор:** Аутентифицированный пользователь.
- **Предусловие:** Пользователь вошел в систему.
- **Основной поток:**
  1. Пользователь нажимает кнопку «Добавить» на главной странице.
  2. Система открывает страницу с формой всех полей модели `Share`.
  3. Пользователь заполняет поля (`figi`, `isin`, `name`, `ticker`, `currency`, `uid`, `last_price`, `is_trend_high`) и нажимает «Сохранить».
  4. Система валидирует данные, сохраняет новую запись в таблице `dashboard_share` и перенаправляет пользователя на главную страницу.
- **Альтернативный поток (неавторизованный доступ):**
  - Анонимный пользователь пытается открыть `/create` — система перенаправляет его на главную страницу без доступа к форме.

### UC-7: Редактирование акции
- **Актор:** Аутентифицированный пользователь.
- **Основной поток:**
  1. Пользователь нажимает «Редактировать» напротив нужной акции.
  2. Система загружает существующие данные акции в форму.
  3. Пользователь корректирует поля и нажимает «Сохранить».
  4. Данные обновляются в БД, пользователя перенаправляет на главную страницу.

### UC-8: Удаление акции
- **Актор:** Аутентифицированный пользователь.
- **Основной поток:**
  1. Пользователь нажимает «Удалить» в строке акции.
  2. Система открывает страницу подтверждения удаления с вопросом «Вы уверены, что хотите удалить инструмент: "[Название]" ?».
  3. Пользователь нажимает кнопку подтверждения «Удалить».
  4. Запись удаляется из БД, происходит редирект на главную страницу.

### UC-9: Управление акциями через программный интерфейс (REST API)
- **Актор:** Внешняя система или клиент API.
- **Основной поток:**
  1. Клиент выполняет HTTP-запросы к `/api/v1/shares/` (GET, POST, PUT, PATCH, DELETE).
  2. Система возвращает JSON-ответы, применяет пагинацию (limit/offset), фильтрацию по тикеру/имени и сортировку.

---

## 3. Бизнес-правила, проверки и ограничения

Ниже представлены правила предметной области и логики работы системы с цитатами исходного кода.

### BR-01: Аутентификация для модификации данных в веб-интерфейсе
- **Описание:** Создавать, редактировать и удалять акции через веб-интерфейс могут только аутентифицированные пользователи. Анонимные пользователи перенаправляются на главную страницу.
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L11-L18) (строки 11–18, 41):
```python
class IsUserAuthenticatedMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated

    @staticmethod
    def handle_no_permission():
        return redirect("dashboard:index")


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
...
```

### BR-02: Публичность каталога и деталей акций
- **Описание:** Просмотр списка акций и детальной информации с графиком доступен всем посетителям без обязательной авторизации (не используются миксины проверки прав).
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L20-L39) (строки 20–39):
```python
class ShareListView(ListView):
    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]

class ShareDetailView(View):
    @staticmethod
    def get(request, pk):
        share = Share.objects.get(id=pk)
        return render(request, "dashboard/detail.html", {"plot_div": get_graph(share), "share": share})
```

### BR-03: Уникальность идентификаторов акции
- **Описание:** Поля `figi`, `ticker` и `uid` акции должны быть строго уникальными в рамках всей системы.
- **Подтверждение в коде:** [dashboard/models.py](dashboard/models.py#L7-L12) (строки 7, 10, 12):
```python
figi = models.CharField(max_length=255, unique=True)
ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
uid = models.CharField(max_length=255, unique=True)
```

### BR-04: Уникальность email при регистрации
- **Описание:** Запрещена регистрация нескольких учетных записей на один и тот же адрес электронной почты.
- **Подтверждение в коде:** [user/forms.py](user/forms.py#L39-L46) (строки 39–46):
```python
user = User.objects.filter(email=email)

if user:
    errors = [
        "Данный e-mail уже зарегистрирован! Введите другой e-mail или"
        " воспользуйтесь формой авторизации."
    ]
    raise ValidationError(errors)
```

### BR-05: Подтверждение пароля при регистрации
- **Описание:** При регистрации значение поля «Пароль» должно в точности совпадать со значением поля «Повторите пароль».
- **Подтверждение в коде:** [user/forms.py](user/forms.py#L35-L37) (строки 35–37):
```python
if password1 and password2 and password1 != password2:
    errors = ["Введенные пароли не совпадают"]
    raise ValidationError(errors)
```

### BR-06: Идентификация пользователя по email
- **Описание:** В качестве имени пользователя (`username`) стандартной модели Django User всегда сохраняется адрес электронной почты. При аутентификации логин сверяется по строке в нижнем регистре (`email.lower()`).
- **Подтверждение в коде:** [user/forms.py](user/forms.py#L51) (строка 51) и [user/views.py](user/views.py#L19) (строка 19):
```python
# user/forms.py:
User.objects.create_user(email, email, password)

# user/views.py:
user = authenticate(
    request, username=form.data["email"].lower(), password=form.data["password"]
)
```

### BR-07: Расчет направления ценового тренда
- **Описание:** Если текущая цена акции стала строго меньше ранее сохраненной цены (`share.last_price > last_price`), то флаг `is_trend_high` устанавливается в `False` (падение). Во всех остальных случаях (рост, равенство или первое получение) тренд считается положительным (`True`).
- **Подтверждение в коде:** [dashboard/tasks.py](dashboard/tasks.py#L16-L22) (строки 16–22):
```python
if share.last_price > last_price:
    is_trend_high = False
else:
    is_trend_high = True
```

### BR-08: Период исторического графика котировок
- **Описание:** График котировок строится по дневным свечам за фиксированный временной интервал — предшествующие 180 календарных дней от текущего момента.
- **Подтверждение в коде:** [dashboard/services/graph.py](dashboard/services/graph.py#L14-L18) (строки 14–18):
```python
for candle in client.get_all_candles(
    figi=share.figi,
    from_=now() - timedelta(days=180),
    interval=CandleInterval.CANDLE_INTERVAL_DAY,
):
```

### BR-09: Интервал периодического фонового обновления
- **Описание:** Периодическая задача обновления котировок `update_last_price` запускается планировщиком Celery Beat каждые 10 секунд.
- **Подтверждение в коде:** [config/celery.py](config/celery.py#L13-L18) (строки 13–18):
```python
app.conf.beat_schedule = {
    "add-every-5-min": {
        "task": "dashboard.tasks.update_last_price",
        "schedule": 10.0,
    },
}
```

### BR-10: Размер страницы пагинации
- **Описание:** Список акций в веб-интерфейсе и REST API по умолчанию разбивается на страницы размером по 100 элементов.
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L25) (строка 25) и [config/settings.py](config/settings.py#L33) (строка 33):
```python
# dashboard/views.py:
paginate_by = 100

# config/settings.py:
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    ...
}
```

### BR-11: Глобальность данных каталога
- **Описание:** Все финансовые инструменты являются общесистемными; в кодовой базе не предусмотрено разделение акций по владельцам, портфелям или спискам отслеживания (нет связей модели `Share` с моделью `User`).
- **Подтверждение в коде:** [dashboard/models.py](dashboard/models.py#L4-L21) (строки 4–21) — модель `Share` не содержит внешних ключей к пользователям.

---

## 4. Восстановленные функциональные требования

Ниже приведен полный нумерованный перечень фактически реализованных требований к системе со ссылками на файлы и фрагментами программного кода.

### 4.1. Модуль каталога и отображения акций

#### FR-01: Табличное отображение каталога акций
- **Требование:** Система должна отображать список всех зарегистрированных акций в виде таблицы с колонками: «Тикер», «Название», «ISIN», «Текущая цена» с валютой.
- **Подтверждение в коде:** [dashboard/templates/dashboard/list.html](dashboard/templates/dashboard/list.html#L18-L26) (строки 18–26):
```html
<thead>
<tr>
    <th scope="col">Тикер</th>
    <th scope="col">Название</th>
    <th scope="col">ISIN</th>
    <th scope="col">Текущая цена</th>
    {% if user.is_authenticated %}
        <th scope="col">Управление</th>
    {% endif %}
</tr>
</thead>
```

#### FR-02: Алфавитная сортировка каталога
- **Требование:** Система должна выполнять сортировку списка акций по наименованию компании в алфавитном порядке.
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L26) (строка 26):
```python
ordering = ["name"]
```

#### FR-03: Постраничная навигация (пагинация)
- **Требование:** Система должна разбивать список акций на страницы по 100 записей и предоставлять кнопки перехода между предыдущей, следующей и номерами страниц.
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L25) (строка 25) и [dashboard/templates/dashboard/list.html](dashboard/templates/dashboard/list.html#L60-L80) (строки 60–80):
```python
paginate_by = 100
```
```html
<div class="btn-group" role="group" aria-label="Item pagination">
    {% if page_obj.has_previous %}
        <a href="?page={{ page_obj.previous_page_number }}" class="btn btn-outline-primary">&laquo;</a>
    {% endif %}
    {% for page_number in page_obj.paginator.page_range %}
        ...
```

#### FR-04: Цветовая индикация рыночного тренда
- **Требование:** Система должна выделять ячейку с текущей ценой зеленым фоном (`mediumseagreen`), если значение `is_trend_high` истинно (`True`), и розовым фоном (`palevioletred`), если значение ложно (`False`).
- **Подтверждение в коде:** [dashboard/templates/dashboard/list.html](dashboard/templates/dashboard/list.html#L35-L40) (строки 35–40):
```html
{% if share.is_trend_high %}
    <td style="background-color: mediumseagreen">
{% else %}
    <td style="background-color: palevioletred">
{% endif %}
{{ share.last_price }} {{ share.currency }}</td>
```

#### FR-05: Навигация к детальной информации по клику на тикер
- **Требование:** При клике на тикер акции в каталоге система должна перенаправлять пользователя на детальную страницу соответствующей акции.
- **Подтверждение в коде:** [dashboard/templates/dashboard/list.html](dashboard/templates/dashboard/list.html#L32) (строка 32):
```html
<td><a href="{% url 'dashboard:detail' share.id %}"> {{share.ticker}} </a></td>
```

#### FR-06: Детальный просмотр и построение графика котировок
- **Требование:** На детальной странице акции система должна отображать наименование инструмента, текущую цену с валютой, время последнего обновления и линейный график Plotly дневных цен закрытия за предшествующие 180 дней.
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L31-L38) (строки 31–38) и [dashboard/services/graph.py](dashboard/services/graph.py#L21-L36) (строки 21–36):
```python
# dashboard/views.py:
def get(request, pk):
    share = Share.objects.get(id=pk)
    return render(
        request,
        "dashboard/detail.html",
        {"plot_div": get_graph(share), "share": share},
    )
```

---

### 4.2. Модуль управления акциями через веб-интерфейс

#### FR-07: Отображение элементов управления только авторизованным пользователям
- **Требование:** Система должна показывать кнопку добавления инструмента («Добавить») и кнопки «Редактировать» и «Удалить» только авторизованным пользователям. Для анонимных пользователей данные элементы должны быть скрыты.
- **Подтверждение в коде:** [dashboard/templates/dashboard/list.html](dashboard/templates/dashboard/list.html#L9-L13) (строки 9–13, 41–50):
```html
{% if user.is_authenticated %}
    <div>
        <a href="{% url 'dashboard:create' %}" class="btn btn-primary">Добавить</a>
    </div>
{% endif %}
```

#### FR-08: Добавление новой акции через форму
- **Требование:** Система должна предоставлять форму создания акции по маршруту `/create` на основе `ShareModelForm` со всеми полями модели и сохранять запись в БД с редиректом на главную страницу.
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L41-L46) (строки 41–46):
```python
class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")
```

#### FR-09: Редактирование существующей акции
- **Требование:** Система должна предоставлять форму редактирования акции по маршруту `/update/<pk>` и сохранять измененные атрибуты в БД с редиректом на главную страницу.
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L49-L55) (строки 49–55):
```python
class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")
```

#### FR-10: Удаление акции с подтверждением
- **Требование:** Система должна отображать экран подтверждения удаления инструмента по маршруту `/delete/<pk>` и удалять запись из БД при подтверждении запроса методом POST.
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L58-L63) (строки 58–63) и [dashboard/templates/dashboard/delete.html](dashboard/templates/dashboard/delete.html#L9-L13) (строки 9–13):
```python
class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")
```

#### FR-11: Блокировка неавторизованного доступа к CRUD-операциям
- **Требование:** При попытке неаутентифицированного пользователя открыть маршруты создания, редактирования или удаления акций система должна выполнять редирект на главную страницу (`dashboard:index`).
- **Подтверждение в коде:** [dashboard/views.py](dashboard/views.py#L11-L18) (строки 11–18):
```python
class IsUserAuthenticatedMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated

    @staticmethod
    def handle_no_permission():
        return redirect("dashboard:index")
```

---

### 4.3. Модуль REST API

#### FR-12: Базовые CRUD-эндпоинты REST API
- **Требование:** Система должна предоставлять программный интерфейс по пути `/api/v1/shares/` с поддержкой методов GET (список и деталь), POST (создание), PUT/PATCH (обновление) и DELETE (удаление).
- **Подтверждение в коде:** [dashboard/api/v1/router.py](dashboard/api/v1/router.py#L5-L6) (строки 5–6) и [dashboard/api/v1/views.py](dashboard/api/v1/views.py#L16-L18) (строки 16–18):
```python
# router.py:
router = routers.DefaultRouter()
router.register(r"shares", ShareViewSet)

# views.py:
class ShareViewSet(viewsets.ModelViewSet):
    serializer_class = ShareSerializer
    queryset = Share.objects.all()
```

#### FR-13: Сериализация полей акции в JSON
- **Требование:** REST API должен возвращать JSON-объект со следующими полями: `id`, `figi`, `isin`, `name`, `ticker`, `currency`, `last_price`, `is_trend_high`, `updated_at`.
- **Подтверждение в коде:** [dashboard/api/v1/serializer.py](dashboard/api/v1/serializer.py#L6-L19) (строки 6–19):
```python
class ShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Share
        fields = (
            "id",
            "figi",
            "isin",
            "name",
            "ticker",
            "currency",
            "last_price",
            "is_trend_high",
            "updated_at",
        )
```

#### FR-14: Фильтрация, поиск и сортировка в REST API
- **Требование:** REST API должен поддерживать точную фильтрацию по полям `name` и `ticker`, регулярный поиск по наименованию (`$name`) и сортировку по `name` и `ticker`.
- **Подтверждение в коде:** [dashboard/api/v1/views.py](dashboard/api/v1/views.py#L10-L22) (строки 10–22):
```python
class ShareFilter(filters.FilterSet):
    class Meta:
        model = Share
        fields = ("name", "ticker")

class ShareViewSet(viewsets.ModelViewSet):
    ...
    filter_backends = (OrderingFilter, filters.DjangoFilterBackend, SearchFilter)
    filterset_class = ShareFilter
    ordering_fields = ["name", "ticker"]
    search_fields = ["$name"]
```

#### FR-15: Пагинация REST API
- **Требование:** REST API должен применять постраничную навигацию `LimitOffsetPagination` с базовым лимитом 100 записей.
- **Подтверждение в коде:** [config/settings.py](config/settings.py#L31-L35) (строки 31–35):
```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}
```

---

### 4.4. Модуль фонового обновления и первоначального импорта котировок

#### FR-16: Первоначальный импорт акций из биржевого API
- **Требование:** Система должна предоставлять консольную команду `python manage.py add_shares`, которая запрашивает через Tinkoff API список всех акций (`client.instruments.shares()`) и сохраняет их в БД методом `get_or_create`.
- **Подтверждение в коде:** [dashboard/management/commands/add_shares.py](dashboard/management/commands/add_shares.py#L11-L22) (строки 11–22):
```python
def handle(self, *args, **options):
    with Client(TINKOFF_TOKEN) as client:
        shares = client.instruments.shares()
        for share in shares.instruments:
            Share.objects.get_or_create(
                figi=share.figi,
                name=share.name,
                isin=share.isin,
                ticker=share.ticker,
                currency=share.currency,
                uid=share.uid,
            )
```

#### FR-17: Планирование фонового опроса цен
- **Требование:** Планировщик Celery Beat должен инициировать запуск задачи `dashboard.tasks.update_last_price` каждые 10 секунд.
- **Подтверждение в коде:** [config/celery.py](config/celery.py#L13-L18) (строки 13–18):
```python
app.conf.beat_schedule = {
    "add-every-5-min": {
        "task": "dashboard.tasks.update_last_price",
        "schedule": 10.0,
    },
}
```

#### FR-18: Фоновое обновление цен акций и фиксация тренда
- **Требование:** Фоновая задача `update_last_price` должна перебирать все зарегистрированные в БД акции, запрашивать для каждой последнюю рыночную цену через внешний сервис `get_last_data`, вычислять изменение тренда и обновлять поля `last_price` и `is_trend_high` в БД.
- **Подтверждение в коде:** [dashboard/tasks.py](dashboard/tasks.py#L8-L26) (строки 8–26):
```python
@app.task
def update_last_price():
    shares = Share.objects.all()

    for share in shares:
        try:
            [last_price, detetime] = get_last_data(share)
            try:
                if share.last_price > last_price:
                    is_trend_high = False
                else:
                    is_trend_high = True
            except Exception as e:
                logger.error(e)
                is_trend_high = True

            Share.objects.filter(id=share.id).update(
                last_price=last_price, is_trend_high=is_trend_high
            )
        except Exception as e:
            logger.error(e)
```

---

### 4.5. Модуль управления учетными записями

#### FR-19: Регистрация нового пользователя
- **Требование:** Система должна обеспечивать регистрацию нового пользователя по маршруту формы регистрации с вводом `email`, `password1` и `password2`. При успехе создается запись пользователя и выполняется автоматический вход в систему с перенаправлением на главную страницу.
- **Подтверждение в коде:** [user/views.py](user/views.py#L44-L50) (строки 44–50) и [user/forms.py](user/forms.py#L48-L53) (строки 48–53):
```python
# user/views.py:
def post(request):
    form = RegistrationForm(request.POST)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard:index")
```

#### FR-20: Аутентификация пользователя
- **Требование:** Система должна выполнять аутентификацию пользователя по введенным `email` и `password`. При корректных данных создается сессия пользователя и происходит перенаправление на главную страницу. При несовпадении выводится предупреждение об ошибке: «Неверный логин или пароль! Повторите попытку.».
- **Подтверждение в коде:** [user/views.py](user/views.py#L16-L33) (строки 16–33):
```python
def post(request):
    form = AuthForm(request.POST)
    user = authenticate(
        request, username=form.data["email"].lower(), password=form.data["password"]
    )
    if user is not None:
        login(request, user)
        return redirect("dashboard:index")
    else:
        return render(
            request,
            "user/auth.html",
            {
                "form": form,
                "error": "Неверный логин или пароль! Повторите попытку.",
            },
        )
```

#### FR-21: Завершение сеанса пользователя (Logout)
- **Требование:** При переходе по маршруту выхода система должна прекращать активный сеанс пользователя (`logout`) и перенаправлять его на главную страницу.
- **Подтверждение в коде:** [user/views.py](user/views.py#L58-L64) (строки 58–64):
```python
class LogoutView(View):
    @staticmethod
    def get(request):
        logout(request)
        return redirect("dashboard:index")
```

---

## 5. Выявленные неоднозначности, противоречия и дефекты реализации

В процессе восстановления требований зафиксированы следующие дефекты реализации, которые **не являются** нормальным поведением системы, а представляют собой технические ошибки:

### Д-1: Ошибка маршрутизации приложения `user`
- **Проблема:** В [config/urls.py](config/urls.py#L7) (строка 7) подключение роутов задано как `path("user", include("user.urls"))` без слеша. Из-за этого URL-пути сливаются в `/userlogin/`, `/userregistration/`, `/userlogout/` вместо стандартных `/user/login/`, `/user/registration/`.
- **Фрагмент кода:** [config/urls.py](config/urls.py#L7) (строка 7):
```python
path("user", include("user.urls")),
```

### Д-2: Падение сервера (HTTP 500) при ошибках валидации регистрации
- **Проблема:** При валидации формы регистрации в `RegistrationView.post` код жестко обращается к `form.errors["__all__"]`. Если ошибка возникла в конкретном поле (например, неверный формат email или короткий пароль), ключа `"__all__"` в словаре нет, что приводит к необработанному `KeyError` и падению сервера с кодом 500 вместо вывода ошибки пользователю.
- **Фрагмент кода:** [user/views.py](user/views.py#L54) (строка 54):
```python
{"form": form, "error": form.errors["__all__"].data[0].message}
```

### Д-3: Отсутствие вызова `form.is_valid()` при авторизации
- **Проблема:** В `AuthView.post` не вызывается `form.is_valid()`; данные извлекаются напрямую из сырого словаря `form.data["email"]` и `form.data["password"]`. При отправке пустого POST-запроса сервер аварийно падает по `KeyError`.
- **Фрагмент кода:** [user/views.py](user/views.py#L17-L20) (строки 17–20):
```python
form = AuthForm(request.POST)
user = authenticate(
    request, username=form.data["email"].lower(), password=form.data["password"]
)
```

### Д-4: Отбрасывание дробной части биржевой цены (копеек / центов)
- **Проблема:** В сервисах котировок из структуры `Quotation` извлекается только целая часть `units`, а нано-часть `nano` (1/10^9) игнорируется. В результате цены усекаются вниз до целого числа (например, 285.75 руб. сохраняется как 285.00 руб.), что искажает реальные рыночные котировки.
- **Фрагмент кода:** [dashboard/services/market_data.py](dashboard/services/market_data.py#L11) (строка 11) и [dashboard/services/graph.py](dashboard/services/graph.py#L20) (строка 20):
```python
# market_data.py:
return [resp.price.units, resp.time]

# graph.py:
y_data.append(candle.close.units)
```

### Д-5: Синхронный блокирующий I/O при открытии детальной страницы
- **Проблема:** В контроллере `ShareDetailView` при каждом обычном HTTP GET-запросе синхронно вызывается сетевой gRPC-метод Tinkoff API за 180 днями свечей. При сетевых задержках или отсутствии токена пользовательский браузер зависает или получает HTTP 500.
- **Фрагмент кода:** [dashboard/views.py](dashboard/views.py#L37) (строка 37):
```python
{"plot_div": get_graph(share), "share": share}
```

### Д-6: Полное отсутствие авторизации и ограничений доступа в REST API
- **Проблема:** В `ShareViewSet` не заданы `permission_classes`. В результате любой анонимный клиент в сети имеет неограниченный доступ к созданию, модификации и удалению акций через эндпоинты `/api/v1/shares/`, тогда как в веб-интерфейсе эти действия защищены миксином.
- **Фрагмент кода:** [dashboard/api/v1/views.py](dashboard/api/v1/views.py#L16-L22) (строки 16–22):
```python
class ShareViewSet(viewsets.ModelViewSet):
    serializer_class = ShareSerializer
    queryset = Share.objects.all()
    # permission_classes не заданы — действует AllowAny
```

### Д-7: Необновление временной метки `updated_at` при фоновом опросе
- **Проблема:** В задаче `update_last_price` для обновления записи используется метод `QuerySet.update()`. В Django ORM метод `update()` генерирует прямой SQL UPDATE без вызова метода `save()` модели, поэтому поле с атрибутом `auto_now=True` (`updated_at`) автоматически не обновляется.
- **Фрагмент кода:** [dashboard/tasks.py](dashboard/tasks.py#L24-L26) (строки 24–26):
```python
Share.objects.filter(id=share.id).update(
    last_price=last_price, is_trend_high=is_trend_high
)
```

### Д-8: Потенциальное падение Celery-задачи при сравнении с `None`
- **Проблема:** Для вновь добавленной акции поле `last_price` равно `None`. Сравнение `share.last_price > last_price` падает с `TypeError: '>' not supported between instances of 'NoneType' and 'int'`, что перехватывается только общим `except Exception` и приводит к скрытой ошибке.
- **Фрагмент кода:** [dashboard/tasks.py](dashboard/tasks.py#L16) (строка 16):
```python
if share.last_price > last_price:
```

### Д-9: Конфликт стилей верстки и crispy-forms
- **Проблема:** В `config/settings.py` подключен пакет `crispy-bootstrap3`, а в базовом шаблоне `dashboard/templates/dashboard/base.html` подключены стили Bootstrap 4/5. Из-за этого поля форм рендерятся с некорректными CSS-классами.
- **Фрагмент кода:** [config/settings.py](config/settings.py#L28-L29) (строки 28–29):
```python
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap3"
CRISPY_TEMPLATE_PACK = "bootstrap3"
```

---

## Резюме по Заданию №2
На основе исходного кода полностью восстановлены 21 функциональное требование (FR-01 — FR-21), 11 бизнес-правил (BR-01 — BR-11) и зафиксированы 9 критических дефектов реализации (Д-1 — Д-9). Все пункты снабжены кликабельными относительными ссылками на файлы проекта и цитатами подтверждающего исходного кода. Документ готов для использования на этапах рефакторинга и тестирования.
