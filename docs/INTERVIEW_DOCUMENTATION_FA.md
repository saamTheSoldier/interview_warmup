# مستند مصاحبه — راهنمای جامع پروژه (سطح Senior)

این سند به‌صورت **مفصل و کامل** همه‌چیز را برای آمادگی مصاحبه پوشش می‌دهد: تکنولوژی‌ها، دیزاین‌پترن‌ها، معماری، طراحی سیستم، پوشه‌بندی و چالش‌ها، با **ارجاع مستقیم به کد پروژه**. اصطلاحات فنی به انگلیسی آمده و مفهوم‌ها توضیح داده شده‌اند. ساختار به‌صورت **پرسش محتمل مصاحبه‌گر → توضیح + ارجاع به کد + پاسخ در سطح Senior** است.

---

## فهرست

1. [تکنولوژی‌های استفاده‌شده](#1-تکنولوژیهای-استفاده‌شده)
2. [معماری کلی سیستم](#2-معماری-کلی-سیستم)
3. [طراحی و پوشه‌بندی (Folder Structure)](#3-طراحی-و-پوشه‌بندی-folder-structure)
4. [دیزاین‌پترن‌ها (Design Patterns)](#4-دیزاین‌پترن‌ها-design-patterns)
5. [چالش‌ها و راه‌حل‌ها در کد](#5-چالش‌ها-و-راه‌حل‌ها-در-کد)
6. [پرسش‌های محتمل مصاحبه با پاسخ Senior](#6-پرسشهای-محتمل-مصاحبه-با-پاسخ-senior)
7. [واژه‌نامهٔ اصطلاحات فنی](#7-واژه‌نامهٔ-اصطلاحات-فنی-انگلیسی-با-توضیح-فارسی)
8. [نقشهٔ سریع: فایل ← مسئولیت](#8-نقشهٔ-سریع-فایل--مسئولیت)
9. [پرسش‌های تکمیلی مصاحبه](#9-پرسشهای-تکمیلی-مصاحبه)

---

## 1. تکنولوژی‌های استفاده‌شده

### 1.1 Python و FastAPI

- **FastAPI**: فریم‌ورک وب **async** برای ساخت API. از **OpenAPI (Swagger)**، **validation** با Pydantic و **Dependency Injection** پشتیبانی می‌کند.
- **ارجاع در پروژه**: نقطهٔ ورود اپلیکیشن در `app/main.py` با `create_app()` و `app = create_app()`. روت‌ها در `app/api/v1/router.py` جمع‌آوری و با `app.include_router(api_router, prefix="/api")` در `main.py` متصل شده‌اند.

### 1.2 PostgreSQL و SQLAlchemy (Async)

- **PostgreSQL**: دیتابیس رابطه‌ای اصلی (Primary Data Store).
- **SQLAlchemy 2**: ORM با پشتیبانی **async** (asyncpg). مدل‌ها در `app/db/models/` (مثلاً `User` در `user.py`، `Item` در `item.py`) و **Base** در `app/db/base.py` تعریف شده‌اند.
- **asyncpg**: درایور async برای PostgreSQL؛ در `app/db/session.py` داخل `create_async_engine(settings.database_url)` استفاده شده است.
- **Connection Pool**: در `session.py` با `pool_size=10` و `max_overflow=20` تنظیم شده تا تحت بار (Scalability) اتصالات را مدیریت کند.
- **پیشنهاد مصاحبه**: «چرا async برای دیتابیس؟» — در درخواست‌های I/O-bound، با async می‌توان در زمان انتظار پاسخ DB، درخواست‌های دیگر را پردازش کرد و throughput بالاتر رفت.

### 1.3 Redis

- **Redis**: برای **Caching**، امکان **Rate Limiting** و به‌عنوان **Result Backend** برای Celery.
- **ارجاع**: `app/cache/redis_client.py` — توابع `cache_get`, `cache_set`, `cache_delete` با **TTL** و **graceful degradation** (در صورت خطا `None` برمی‌گردانند تا اپ از کار نیفتد).
- **استفاده در جریان**: در `app/services/item_service.py` متد `get_by_id` ابتدا از کش با کلید `item:{id}` می‌خواند؛ در **cache miss** از دیتابیس می‌خواند و نتیجه را در Redis با TTL ثابت (مثلاً ۳۰۰ ثانیه) ذخیره می‌کند.

### 1.4 Elasticsearch

- **Elasticsearch**: موتور **Full-Text Search** و **Analytics**.
- **ارجاع**: `app/search/elasticsearch_client.py` — ایندکس `items` با mapping در `ensure_items_index()`؛ جستجو با `search_items()` و کوئری **multi_match** با **fuzziness** روی `title` و `description`. ایندکس/حذف سند با `index_item()` و `remove_item_from_index()`.
- **چرا جدا از PostgreSQL؟** — برای جستجوی متنی و فازی، Elasticsearch بهینه‌تر است؛ دادهٔ اصلی در PostgreSQL می‌ماند و Elasticsearch برای search و analytics استفاده می‌شود (تفکیک مسئولیت).

### 1.5 Celery و RabbitMQ (Queue Management)

- **Celery**: صف کار (Job Queue) برای اجرای تسک‌های **async** خارج از چرخهٔ درخواست HTTP (مشابه Sidekiq در Ruby).
- **RabbitMQ**: **Message Broker** برای Celery؛ پروتکل AMQP.
- **ارجاع**: `app/queue/celery_app.py` — تعریف `Celery` با `broker=celery_broker_url` و `backend=redis_url`. تسک‌ها در `app/queue/tasks.py`؛ مثلاً `index_item_task` که ایندکس کردن آیتم در Elasticsearch را بعد از create/update انجام می‌دهد (الگوی **Event-Driven**: API پیام می‌فرستد، Worker مصرف می‌کند).
- **چرا صف؟** — ایندکس کردن در ES نباید زمان پاسخ API را طولانی کند؛ با صف، پاسخ سریع برمی‌گردد و کار سنگین در Worker انجام می‌شود؛ در صورت خطا **retry** (مثلاً `max_retries=3`) هم داریم.

### 1.6 Docker و Docker Compose

- **Docker**: کانتینرسازی اپلیکیشن و سرویس‌ها.
- **Dockerfile**: در روت پروژه؛ **Multi-stage build** (مرحلهٔ builder برای نصب وابستگی‌ها، مرحلهٔ نهایی فقط runtime) برای کاهش حجم image و بهبود کش لایه‌ها. اجرا با **non-root user** (`appuser`) برای امنیت.
- **docker-compose.yml**: تعریف سرویس‌های **api**, **celery_worker**, **db** (PostgreSQL), **redis**, **rabbitmq**, **elasticsearch**, **prometheus**, **grafana** با **healthcheck** و **depends_on** تا ترتیب بالا آمدن و وابستگی‌ها درست باشد.

### 1.7 Prometheus و Grafana (Monitoring & Observability)

- **Prometheus**: جمع‌آوری **metrics** (مثل درخواست‌ها، خطاها).
- **Grafana**: داشبورد و نمودار روی دادهٔ Prometheus.
- **ارجاع**: در `app/main.py` با `make_asgi_app()` از `prometheus_client` اپلیکیشن متریک در مسیر `/metrics` mount شده است. تنظیمات scrape در `monitoring/prometheus.yml` و دیتاسورس Grafana در `monitoring/grafana/provisioning/datasources/`.

### 1.8 TDD و BDD

- **TDD (Test-Driven Development)**: تست‌های واحد و API با **pytest** و **pytest-asyncio**.
- **BDD (Behavior-Driven Development)**: سناریوهای Gherkin با **pytest-bdd**؛ رفتار از دید کاربر/اپراتور.
- **ارجاع**: تست‌ها در `tests/` — مثلاً `tests/test_health.py`, `tests/test_items_api.py`؛ فیچرها در `tests/features/health.feature` و stepها در `tests/step_defs/test_health_bdd.py`. در `tests/conftest.py` fixtureهای **client**, **session**, **test_user**, **auth_headers** و override کردن `get_db` برای ایزوله بودن تست‌ها تعریف شده است.

### 1.9 Git و Version Control — Alembic

- **Alembic**: مایگریشن‌های دیتابیس (Schema Versioning)؛ هر تغییر اسکیمای DB به‌صورت نسخه‌دار و قابل برگشت است.
- **ارجاع**: `alembic/` — `env.py` برای اتصال به DB و اجرای مایگریشن؛ `alembic/versions/001_initial.py` برای ایجاد جداول `users` و `items` با ایندکس‌ها (مثلاً `ix_users_email`, `ix_items_owner_id`).

### 1.10 CI/CD (GitHub Actions)

- **Pipeline**: روی push/PR به شاخه‌های `main` و `develop` اجرا می‌شود.
- **ارجاع**: `.github/workflows/ci.yml` — سرویس‌های **PostgreSQL, Redis, RabbitMQ**؛ نصب وابستگی‌ها؛ اجرای **pytest**؛ لینت با **ruff** و بررسی فرمت با **black**. در مصاحبه می‌توان گفت: «تست و کیفیت کد به‌صورت خودکار قبل از merge چک می‌شود.»

---

## 2. معماری کلی سیستم

### 2.1 معماری لایه‌ای (Layered Architecture)

جریان درخواست از بالا به پایین است:

1. **API Layer (Controllers)** — `app/api/v1/endpoints/`  
   فقط HTTP: پارامترها، validation، فراخوانی سرویس و برگرداندن پاسخ. منطق کسب‌وکار اینجا نیست (**Thin Controller**).

2. **Service Layer (Application / Use Cases)** — `app/services/`  
   هماهنگی بین Repository، Cache، Queue و Search. مثلاً `ItemService` در `item_service.py`: create → ذخیره در DB + ارسال به صف؛ get_by_id → ابتدا Cache، سپس DB و پر کردن Cache.

3. **Data Access Layer (Repository)** — `app/db/repositories/`  
   فقط دسترسی به دیتابیس؛ کوئری‌ها و بهینه‌سازی (مثل جلوگیری از N+1) اینجا متمرکز است.

4. **Infrastructure** — Cache (`app/cache/`), Search (`app/search/`), Queue (`app/queue/`)  
   سرویس‌های خارجی و ارتباط با Redis، Elasticsearch و Celery.

این تفکیک باعث می‌شود تست (مثلاً mock کردن Repository)، تعویض دیتابیس یا اضافه کردن کش بدون شکستن لایهٔ بالایی ممکن باشد.

### 2.2 جریان داده برای یک «ایتم» (End-to-End)

- **Create**:  
  `POST /api/v1/items` → `items.py` (endpoint) → `ItemService.create()` → `ItemRepository.add()` → commit در session → `index_item_task.delay(...)` (صف) → پاسخ 201. Worker بعداً ایندکس را در Elasticsearch به‌روز می‌کند.
- **Read (با کش)**:  
  `GET /api/v1/items/{id}` → `ItemService.get_by_id()` → ابتدا `cache_get("item:{id}")`؛ در صورت miss → `ItemRepository.get_by_id_with_owner()` → `cache_set(...)` → پاسخ.
- **Update**:  
  مثل create؛ بعد از به‌روزرسانی در DB، کش با `cache_delete("item:{id}")` باطل و دوباره `index_item_task.delay(...)` صف می‌شود.
- **Delete**:  
  حذف از DB، حذف از کش، و `remove_item_from_index(id)` در `elasticsearch_client.py`.

### 2.3 Event-Driven و Decoupling

ایندکس کردن در Elasticsearch **در مسیر پاسخ HTTP** انجام نمی‌شود؛ فقط یک **event** (تسک) به صف فرستاده می‌شود. مزایا: پاسخ سریع‌تر، تحمل خطا (retry در Worker)، و امکان scale کردن Workerها جدا از API.

---

## 3. طراحی و پوشه‌بندی (Folder Structure)

```
interviews/
├── app/
│   ├── __init__.py
│   ├── main.py              # نقطه ورود، lifespan، CORS، mount /metrics، include_router
│   ├── config.py            # Settings (Pydantic)، get_settings() با lru_cache
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── router.py    # جمع‌آوری endpointها با prefix /v1
│   │       └── endpoints/
│   │           ├── health.py
│   │           ├── users.py
│   │           ├── items.py
│   │           └── search.py
│   ├── core/
│   │   ├── security.py      # hash/verify password، JWT encode/decode
│   │   └── dependencies.py  # get_current_user_id، CurrentUserId، HTTPBearer
│   ├── db/
│   │   ├── base.py          # DeclarativeBase
│   │   ├── session.py       # engine، async_session_maker، get_db، DbSession
│   │   ├── models/         # User، Item
│   │   └── repositories/   # BaseRepository، UserRepository، ItemRepository
│   ├── schemas/             # Pydantic: UserCreate، UserResponse، ItemCreate، ItemUpdate، ItemResponse، ...
│   ├── services/           # ItemService
│   ├── cache/               # redis_client: get/set/delete
│   ├── search/              # elasticsearch_client: index، search، remove
│   └── queue/               # celery_app، tasks (index_item_task، ...)
├── alembic/
├── monitoring/              # prometheus.yml، grafana provisioning
├── tests/                   # conftest، test_*.py، features، step_defs
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .github/workflows/ci.yml
```

**چرا این ساختار؟**

- **api/v1**: امکان نسخه‌گذاری API (Versioning)؛ در آینده می‌توان v2 اضافه کرد بدون شکستن v1.
- **core**: منطق مشترک امنیت و وابستگی‌ها (auth، session) در یک جا.
- **db/repositories**: تمام کوئری‌های مربوط به هر entity در یک کلاس؛ جایگاه واحد برای بهینه‌سازی و تست.
- **schemas**: قرارداد API (ورودی/خروجی) و validation در Pydantic؛ جدا از مدل‌های ORM.

---

## 4. دیزاین‌پترن‌ها (Design Patterns)

### 4.1 Repository Pattern

- **مفهوم**: لایهٔ انتزاعی روی دیتابیس؛ بقیهٔ اپ با «ذخیره/بازیابی موجودیت» کار می‌کنند، نه با SQL مستقیم.
- **در پروژه**:  
  - `app/db/repositories/base_repository.py`: کلاس جنریک `BaseRepository[ModelType]` با متدهای `get_by_id`, `get_many`, `add`, `delete`.  
  - `ItemRepository` و `UserRepository` از آن ارث می‌برند و متدهای خاص (مثل `get_by_id_with_owner`, `get_by_email`) را اضافه می‌کنند.
- **فایده**: تست با mock کردن Repository؛ تغییر نوع دیتابیس یا کوئری در یک نقطه؛ رعایت **Single Responsibility** و **Dependency Inversion** (سرویس به interface داده وابسته است، نه به پیاده‌سازی).

### 4.2 Dependency Injection (DI)

- **مفهوم**: وابستگی‌ها (مثل session دیتابیس یا user جاری) از بیرون به تابع/کلاس داده می‌شوند تا کد قابل تست و انعطاف‌پذیر باشد.
- **در پروژه**:  
  - FastAPI با `Depends(get_db)` برای هر endpoint یک `AsyncSession` می‌دهد (`app/db/session.py`: `DbSession = Annotated[AsyncSession, Depends(get_db)]`).  
  - در `app/api/v1/endpoints/items.py` تابع `_get_item_service(session)` سرویس را با `ItemRepository(session)` و `UserRepository(session)` می‌سازد؛ یعنی session از بالا تزریق می‌شود.  
  - احراز هویت با `CurrentUserId = Annotated[int, Depends(get_current_user_id)]` در endpointهای محافظت‌شده استفاده شده است.

### 4.3 Factory (برای سرویس)

- **در پروژه**: تابع `_get_item_service(session)` در `items.py` در عمل یک **Factory** است: با توجه به session جاری، یک نمونهٔ `ItemService` با repositoryهای تزریق‌شده برمی‌گرداند. هر درخواست session خودش را دارد، پس سرویس هم per-request ساخته می‌شود.

### 4.4 Cache-Aside (Lazy Loading برای کش)

- **مفهوم**: اپ اول از کش می‌خواند؛ در صورت miss از منبع اصلی (DB) می‌خواند و نتیجه را در کش می‌نویسد. در به‌روزرسانی/حذف، کش مربوطه invalidate می‌شود.
- **در پروژه**: در `ItemService.get_by_id()` ابتدا `cache_get(CACHE_PREFIX + str(id))`؛ در miss، خواندن از `item_repo.get_by_id_with_owner(id)` و سپس `cache_set(..., resp.model_dump(mode="json"), CACHE_TTL)`. در `update` و `delete` فراخوانی `cache_delete(CACHE_PREFIX + str(id))` در `item_service.py` دیده می‌شود.

### 4.5 Event-Driven (Producer–Consumer)

- **مفهوم**: یک بخش رویداد را منتشر می‌کند (مثلاً «آیتم ساخته شد») و بخش دیگر بدون وابستگی زمانی مستقیم آن را مصرف می‌کند.
- **در پروژه**: API بعد از create/update آیتم، `index_item_task.delay(_item_to_doc(item))` را صدا می‌زند (Producer). Celery Worker تسک را از RabbitMQ می‌گیرد و `index_item` را در Elasticsearch اجرا می‌کند (Consumer). کد در `app/services/item_service.py` (create/update) و `app/queue/tasks.py` (index_item_task).

### 4.6 Single Responsibility Principle (SRP)

- **مفهوم**: هر کلاس/ماژول یک دلیل برای تغییر داشته باشد.
- **در پروژه**:  
  - Endpointها فقط HTTP و فراخوانی سرویس.  
  - `ItemService` فقط use caseهای آیتم (create, get, list, update, delete) و هماهنگی با cache/queue.  
  - Repositoryها فقط دسترسی به داده؛ Security فقط هش و JWT در `core/security.py`.

### 4.7 Dependency Inversion Principle (DIP)

- **مفهوم**: ماژولهای سطح بالا به انتزاع (مثلاً interface) وابسته باشند، نه به پیاده‌سازی سطح پایین.
- **در پروژه**: سرویس به `ItemRepository` و `UserRepository` وابسته است؛ در تست می‌توان Mock Repository تزریق کرد. خود Repository به `AsyncSession` وابسته است که توسط FastAPI تزریق می‌شود؛ پس وابستگی از بالا به پایین معکوس است.

---

## 5. چالش‌ها و راه‌حل‌ها در کد

| چالش | محل در کد | راه‌حل |
|------|-----------|--------|
| **اتصال‌های باز و نشت (Connection leak)** | `app/db/session.py` | `get_db()` با `async with` و در بلوک `finally` فراخوانی `session.close()`؛ در صورت exception قبل از آن `rollback()`. |
| **N+1 Query** | `app/db/repositories/item_repository.py` | استفاده از `selectinload(Item.owner)` در `get_by_id_with_owner` و `get_many_with_owner` تا رابطهٔ owner در یک یا دو کوئری جدا بارگذاری شود، نه به‌ازای هر آیتم. |
| **کش نادرست بعد از به‌روزرسانی** | `app/services/item_service.py` | بعد از `update` و قبل از بازگرداندن پاسخ، `cache_delete(CACHE_PREFIX + str(id))` فراخوانی می‌شود. |
| **مسدود شدن پاسخ API به‌خاطر ایندکس** | `app/services/item_service.py` و `app/queue/tasks.py` | به‌جای فراخوانی مستقیم Elasticsearch در request، `index_item_task.delay(...)`؛ اجرا در Worker. |
| **خطای Redis/ES و سقوط اپ** | `app/cache/redis_client.py` و `app/search/elasticsearch_client.py` | در `cache_get`/`cache_set`/`cache_delete` و در `search_items`/`index_item` با try/except در صورت خطا مقدار بی‌خطر برمی‌گردد (None یا []). **Graceful degradation**. |
| **امنیت: پسورد و توکن** | `app/core/security.py` | پسورد با **bcrypt** هش و هرگز ذخیرهٔ plain text نیست؛ JWT با **exp** و اعتبارسنجی در `decode_access_token`. |
| **تنظیمات پراکنده** | `app/config.py` | یک کلاس `Settings` با Pydantic؛ خواندن از env و فایل `.env`؛ `get_settings()` با `lru_cache` تا فقط یک بار لود شود. |
| **تست بدون دیتابیس واقعی** | `tests/conftest.py` | override کردن `get_db` با session تست (مثلاً روی SQLite در حافظه) و fixtureهای `client`, `test_user`, `auth_headers`. |

---

## 6. پرسش‌های محتمل مصاحبه با پاسخ Senior

### س: چرا از Async (غیرهمگام) استفاده کردید و کجاها؟

**پاسخ:** در جاهایی که I/O زیاد است (دیتابیس، Redis، Elasticsearch، درخواست HTTP خارجی)، با async یک worker می‌تواند در زمان انتظار پاسخ، درخواست دیگری را پردازش کند؛ در نتیجه **throughput** بالاتر و استفادهٔ بهینه از CPU. در پروژه:  
- FastAPI به‌صورت async؛  
- `app/db/session.py`: موتور با `create_async_engine` و `AsyncSession`؛  
- `app/cache/redis_client.py`: کلاینت `redis.asyncio`؛  
- `app/search/elasticsearch_client.py`: `AsyncElasticsearch`.  
Celery به‌صورت sync است؛ برای فراخوانی توابع async داخل تسک از یک event loop موقت (`_run_async` در `app/queue/tasks.py`) استفاده شده است.

---

### س: مشکل N+1 را چطور حل کردید؟

**پاسخ:** وقتی لیست آیتم‌ها را با رابطهٔ `owner` برمی‌گردانیم، اگر برای هر آیتم جداگانه به دیتابیس برویم تا owner را بگیریم، به N+1 کوئری می‌رسیم. راه‌حل **Eager Loading** است: بارگذاری رابطه در همان کوئری (یا یک کوئری اضافهٔ کنترل‌شده). در `app/db/repositories/item_repository.py` از `selectinload(Item.owner)` در متدهای `get_by_id_with_owner` و `get_many_with_owner` استفاده شده تا SQLAlchemy در یک بار همهٔ ownerهای موردنیاز را با یک یا دو کوئری بیاورد، نه به‌ازای هر سطر.

---

### س: استراتژی کش (Caching Strategy) شما چیست؟

**پاسخ:** **Cache-Aside (Lazy Loading)**:  
- خواندن: اول از Redis با کلید مثلاً `item:{id}` می‌خوانیم؛ در صورت miss از PostgreSQL و سپس پر کردن کش با TTL ثابت (مثلاً ۳۰۰ ثانیه). کد در `ItemService.get_by_id()` در `app/services/item_service.py`.  
- نوشتن/به‌روزرسانی/حذف: بعد از هر تغییر در دیتا، با `cache_delete("item:" + str(id))` کش آن رکورد باطل می‌شود تا در بار بعد از DB دادهٔ به‌روز خوانده شود. این کار در متدهای `update` و `delete` همان سرویس انجام شده است.

---

### س: اگر Redis یا Elasticsearch down باشد چه می‌شود؟

**پاسخ:** **Graceful degradation**:  
- در `app/cache/redis_client.py` توابع `cache_get`, `cache_set`, `cache_delete` در بلوک try/except در صورت خطا به‌جای پرتاب exception، مقدار بی‌خطر برمی‌گردانند (مثلاً `None` یا `False`). پس در miss یا خطای Redis، اپ به DB fallback می‌کند و کرش نمی‌کند.  
- در `app/search/elasticsearch_client.py` توابعی مثل `search_items` و `index_item` در صورت خطا لیست خالی یا `False` برمی‌گردانند. جستجو در آن لحظه خالی می‌شود ولی سرویس بالا می‌ماند. برای ایندکس، Celery با retry می‌تواند بعداً دوباره تلاش کند.

---

### س: چرا ایندکس کردن در Elasticsearch را داخل API صدا نزدید؟

**پاسخ:** چون ایندکس کردن یک عملیات سنگین و وابسته به سرویس خارجی است؛ اگر داخل همان request انجام شود، زمان پاسخ بالا می‌رود و در صورت خطای ES کل درخواست با خطا مواجه می‌شود. با **صف (Celery + RabbitMQ)** فقط یک پیام به صف فرستاده می‌شود و پاسخ بلافاصله برگردانده می‌شود؛ Worker در پس‌زمینه ایندکس را انجام می‌دهد و در صورت خطا با **retry** (مثلاً `max_retries=3` در `index_item_task`) دوباره تلاش می‌کند. این الگو **event-driven** و **decoupling** بین API و موتور جستجو را نشان می‌دهد. کد در `app/services/item_service.py` (create/update) و `app/queue/tasks.py`.

---

### س: SOLID را در این پروژه کجا رعایت کردید؟

**پاسخ:**  
- **S (Single Responsibility)**: هر لایه یک مسئولیت — endpointها فقط HTTP؛ Repository فقط دسترسی به داده؛ Service فقط use caseها؛ Security فقط هش و JWT.  
- **O (Open/Closed)**: با Repository و سرویس می‌توان بدون تغییر endpoint، پیاده‌سازی جدید (مثلاً کش دیگر یا دیتابیس دیگر) اضافه کرد.  
- **L (Liskov)**: زیرکلاس‌های Repository (مثل `ItemRepository`) جایگزین پایه را بدون شکستن انتظار caller می‌پذیرند.  
- **I (Interface Segregation)**: BaseRepository فقط متدهای عمومی CRUD را در یک نقطه جمع می‌کند؛ هر repository فقط متدهای لازم خودش را expose می‌کند.  
- **D (Dependency Inversion)**: سرویس به Repository و session وابسته است؛ این وابستگی‌ها از طریق constructor و FastAPI Depends تزریق می‌شوند، نه ساخته شدن داخل سرویس؛ پس وابستگی به انتزاع/interface است و در تست می‌توان mock تزریق کرد.

---

### س: چطور امنیت احراز هویت را پیاده کردید؟

**پاسخ:**  
- **پسورد**: در `app/core/security.py` با **bcrypt** (از طریق `passlib`) هش می‌شود و فقط هش در DB ذخیره می‌شود؛ مقایسه با `verify_password` به‌صورت constant-time است.  
- **جلسه/توکن**: بعد از لاگین موفق، یک **JWT** با `create_access_token(user.id)` ساخته می‌شود (فیلد `sub` و `exp`). در endpointهای محافظت‌شده از وابستگی `get_current_user_id` استفاده شده که هدر `Authorization: Bearer <token>` را می‌خواند و با `decode_access_token` اعتبارسنجی می‌کند؛ در صورت نامعتبر یا منقضی، 401 برمی‌گرداند. کد در `app/core/dependencies.py` و استفادهٔ `CurrentUserId` در `app/api/v1/endpoints/items.py` برای create/update/delete.

---

### س: چرا از Repository استفاده کردید به‌جای نوشتن مستقیم کوئری در endpoint یا سرویس؟

**پاسخ:**  
- **متمرکز کردن کوئری‌ها**: همهٔ دسترسی به جدول آیتم در `ItemRepository` است؛ بهینه‌سازی (مثل selectinload) و تغییرات بعدی در یک جا انجام می‌شود.  
- **تست‌پذیری**: در تست می‌توان یک Mock Repository به سرویس داد و بدون دیتابیس واقعی منطق سرویس را تست کرد.  
- **Dependency Inversion**: لایهٔ بالایی به «قابلیت دسترسی به داده» وابسته است، نه به جزئیات SQL یا ORM؛ در صورت تعویض دیتابیس یا ORM فقط لایهٔ Repository عوض می‌شود.

---

### س: معماری را از نظر کلان چطور توضیح می‌دهید؟

**پاسخ:** یک **Layered Architecture** با لایه‌های مشخص:  
- **Presentation (API)**: `app/api/v1/endpoints/` — فقط HTTP و validation.  
- **Application (Service)**: `app/services/` — use caseها و هماهنگی بین DB، کش، صف و جستجو.  
- **Domain**: موجودیت‌ها در `app/db/models/` و قراردادهای داده در `app/schemas/`.  
- **Data Access**: `app/db/repositories/`.  
- **Infrastructure**: `app/cache/`, `app/search/`, `app/queue/` برای Redis، Elasticsearch و Celery.  
جریان درخواست یک‌طرفه از بالا به پایین است؛ وابستگی‌ها با DI از بیرون تزریق می‌شوند تا لایه‌ها loosely coupled باشند و قابل تست و تعویض باشند.

---

### س: چرا Multi-stage در Dockerfile؟

**پاسخ:** در مرحلهٔ اول (builder) وابستگی‌ها نصب و در یک venv قرار می‌گیرند؛ در مرحلهٔ نهایی فقط آن venv و کد اپ کپی می‌شود، بدون ابزارهای build و لیست پکیج‌های اضافی. نتیجه: **image کوچک‌تر**، سطح حمله کمتر، و کش لایه‌های Docker بهتر کار می‌کند چون تغییر کد فقط لایهٔ آخر را عوض می‌کند. علاوه بر این، اجرای کانتینر با کاربر non-root (`appuser`) برای امنیت انجام شده است.

---

### س: در CI چه کارهایی انجام می‌دهید؟

**پاسخ:** در `.github/workflows/ci.yml` روی push/PR به `main` و `develop`:  
- بالا آوردن سرویس‌های PostgreSQL، Redis و RabbitMQ؛  
- نصب وابستگی‌ها و اجرای **pytest** با env مناسب؛  
- لینت با **ruff** و بررسی فرمت با **black**.  
هدف این است که قبل از merge، تست و کیفیت کد به‌صورت خودکار چک شود و در صورت شکست، merge مسدود شود (اگر continue-on-error حذف شود).

---

### س: TDD و BDD در این پروژه یعنی چه؟

**پاسخ:**  
- **TDD**: تست‌های واحد و یکپارچه با pytest نوشته شده‌اند (مثلاً `tests/test_health.py`, `tests/test_items_api.py`)؛ با fixtureهای `client`, `session`, `test_user`, `auth_headers` در `conftest.py` و override کردن `get_db` می‌توان endpointها را بدون دیتابیس واقعی یا با SQLite تست کرد.  
- **BDD**: رفتار از دید کاربر/اپراتور با زبان Gherkin در `tests/features/health.feature` تعریف شده و با **pytest-bdd** به stepهای Python در `tests/step_defs/test_health_bdd.py` وصل شده است؛ مثلاً «وقتی GET /api/v1/health را می‌زنم، وضعیت 200 و status برابر ok باشد». این برای توافق با ذینفعان روی رفتار و مستندسازی سناریوها مفید است.

---

---

## 7. واژه‌نامهٔ اصطلاحات فنی (انگلیسی با توضیح فارسی)

- **API (Application Programming Interface)**: رابط برنامه‌نویسی؛ در این پروژه یعنی endpointهای HTTP که کلاینت با آن‌ها با سرور صحبت می‌کند.
- **Async / Asynchronous**: غیرهمگام؛ اجرای کد بدون مسدود کردن thread در زمان انتظار I/O (مثل پاسخ دیتابیس).
- **Cache-Aside**: الگوی کش‌گذاری که در آن اپ اول از کش می‌خواند، در صورت نبود از منبع اصلی می‌خواند و نتیجه را در کش می‌نویسد؛ در به‌روزرسانی کش باطل می‌شود.
- **Connection Pool**: مجموعهٔ اتصال‌های ازپیش‌ساخته به دیتابیس که بین درخواست‌ها استفاده می‌شوند تا هزینهٔ باز/بسته کردن اتصال کم شود.
- **Dependency Injection (DI)**: تزریق وابستگی؛ دادن وابستگی‌ها (مثل session یا سرویس) از بیرون به تابع/کلاس به‌جای ساخت داخل آن.
- **Event-Driven**: معماری که در آن اجزا با ارسال و مصرف رویداد/پیام با هم ارتباط دارند، نه با فراخوانی مستقیم.
- **Eager Loading**: بارگذاری رابطه‌های وابسته در همان کوئری (یا کوئری کم‌عدد) برای جلوگیری از N+1.
- **Graceful Degradation**: وقتی یک سرویس فرعی (مثل Redis) خراب است، اپ با کاهش قابلیت (مثلاً بدون کش) به کارش ادامه می‌دهد به‌جای کرش.
- **JWT (JSON Web Token)**: توکن امضاشده که هویت و claimها را حمل می‌کند؛ در هدر Authorization برای احراز هویت API استفاده می‌شود.
- **Layered Architecture**: معماری لایه‌ای؛ تفکیک مسئولیت به لایه‌های مشخص (مثلاً API، Service، Repository).
- **Message Broker**: سرویسی که پیام را از Producer می‌گیرد و به Consumer می‌رساند (مثل RabbitMQ برای Celery).
- **N+1 Problem**: وقتی برای N رکورد، یک کوئری برای لیست و N کوئری جدا برای رابطه‌ها زده می‌شود؛ با Eager Loading حل می‌شود.
- **ORM (Object-Relational Mapping)**: نگاشت شیء به جدول؛ در این پروژه SQLAlchemy.
- **Repository Pattern**: لایهٔ انتزاعی که تمام دسترسی به دادهٔ یک entity را در یک کلاس جمع می‌کند.
- **REST (Representational State Transfer)**: سبک طراحی API مبتنی بر منابع (Resource) و افعال HTTP (GET, POST, PUT, DELETE).
- **SOLID**: پنج اصل طراحی شیءگرا (Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion).
- **TTL (Time To Live)**: مدت زمان اعتبار یک رکورد در کش؛ بعد از آن منقضی می‌شود.
- **Thin Controller**: کنترلری که فقط درخواست/پاسخ و فراخوانی سرویس را انجام می‌دهد و منطق کسب‌وکار در لایهٔ دیگر است.

---

## 8. نقشهٔ سریع: فایل ← مسئولیت

| فایل / پوشه | مسئولیت اصلی |
|-------------|---------------|
| `app/main.py` | ساخت FastAPI، lifespan، CORS، mount کردن `/metrics`، include کردن روت‌های API |
| `app/config.py` | تنظیمات از env با Pydantic؛ `get_settings()` با cache |
| `app/db/session.py` | موتور async، session factory، `get_db()` و نوع `DbSession` |
| `app/db/base.py` | `DeclarativeBase` برای مدل‌های SQLAlchemy |
| `app/db/models/user.py`, `item.py` | موجودیت‌های User و Item و رابطه‌ها |
| `app/db/repositories/base_repository.py` | Repository جنریک با get_by_id، get_many، add، delete |
| `app/db/repositories/item_repository.py` | کوئری‌های Item با selectinload برای owner |
| `app/db/repositories/user_repository.py` | کوئری‌های User مثلاً get_by_email |
| `app/schemas/*.py` | Pydantic برای request/response و validation |
| `app/core/security.py` | هش پسورد، ساخت و اعتبارسنجی JWT |
| `app/core/dependencies.py` | get_current_user_id، CurrentUserId، HTTPBearer |
| `app/services/item_service.py` | use caseهای آیتم + کش + صف ایندکس |
| `app/cache/redis_client.py` | اتصال Redis، cache_get/set/delete با TTL و graceful failure |
| `app/search/elasticsearch_client.py` | ایندکس، جستجو، حذف از ایندکس؛ ensure_items_index |
| `app/queue/celery_app.py` | تعریف Celery با broker و backend |
| `app/queue/tasks.py` | تسک index_item_task و dummy_health_task |
| `app/api/v1/router.py` | جمع‌آوری endpointها با prefix و tags |
| `app/api/v1/endpoints/items.py` | CRUD آیتم؛ فراخوانی ItemService و مدیریت 404/401 |
| `app/api/v1/endpoints/users.py` | register، login و برگرداندن JWT |
| `app/api/v1/endpoints/search.py` | endpoint جستجو با q، skip، limit |
| `app/api/v1/endpoints/health.py` | liveness و readiness |
| `docker-compose.yml` | تعریف سرویس‌های api، celery_worker، db، redis، rabbitmq، elasticsearch، prometheus، grafana |
| `Dockerfile` | Multi-stage build و اجرا با non-root user |
| `alembic/` | مایگریشن اسکیمای دیتابیس |
| `tests/conftest.py` | fixtureهای session، client، test_user، auth_headers و overrideی get_db |
| `.github/workflows/ci.yml` | اجرای pytest، ruff، black روی push/PR |

---

## 9. پرسش‌های تکمیلی مصاحبه

### س: Pagination را چطور پیاده کردید و چرا این روش؟

**پاسخ:** در endpoint لیست آیتم‌ها (`GET /api/v1/items`) از پارامترهای query **skip** و **limit** استفاده شده (`app/api/v1/endpoints/items.py`). مقادیر با `Query(0, ge=0)` و `Query(20, ge=1, le=settings.max_page_size)` اعتبارسنجی می‌شوند تا منفی نباشند و limit از حداکثر مجاز (مثلاً ۱۰۰) بیشتر نشود. در `ItemRepository.get_many_with_owner` همین skip و limit به `select(...).offset(skip).limit(limit)` داده می‌شود تا از دیتابیس فقط همان صفحه بارگذاری شود (**offset/limit pagination**). برای حجم خیلی بالا می‌توان در آینده **cursor-based pagination** با id یا created_at در نظر گرفت تا زیر بار زیاد پایدارتر باشد.

---

### س: چرا Pydantic برای تنظیمات و schemaها؟

**پاسخ:** **Type safety** و **validation در یک نقطه**:  
- در `config.py` با Pydantic Settings همهٔ envها با نوع مشخص خوانده می‌شوند و در صورت مقدار نامعتبر، اپ از همان اول بالا نمی‌آید.  
- در API با schemaهای Pydantic (مثل `ItemCreate`, `ItemResponse`) ورودی و خروجی اعتبارسنجی و سریالایز می‌شوند و مستندات OpenAPI خودکار تولید می‌شود. این کار خطاهای runtime را کم و قرارداد API را شفاف می‌کند.

---

### س: CORS را چرا و کجا تنظیم کردید؟

**پاسخ:** وقتی فرانت‌اند از دامنهٔ دیگری (مثلاً localhost:3000) به API (مثلاً localhost:8000) درخواست می‌زند، مرورگر به‌طور پیش‌فرض آن را مسدود می‌کند مگر سرور هدرهای CORS مناسب بفرستد. در `app/main.py` با `CORSMiddleware` و `allow_origins=["*"]` (در پروداکشن باید دامنهٔ مشخص باشد) اجازهٔ درخواست از هر origin داده شده است تا در توسعه و مصاحبه بدون مشکل فرانت و بک جدا کار کنند.

---

### س: اگر یک درخواست همزمان روی یک آیتم update و دیگری get کند، چه می‌شود؟

**پاسخ:** برای **get**: اگر از کش خوانده شود، ممکن است تا لحظهٔ invalidate شدن کش (بعد از commitِ update) دادهٔ قدیمی برگردد؛ با TTL و invalidate بعد از update سعی می‌کنیم ناهماهنگی کوتاه باشد. برای **update**: دو درخواست update همزمان به دو تراکنش جدا می‌روند؛ دیتابیس با قفل سطر یا سطح ایزوله‌ای که داریم (مثلاً READ COMMITTED) یکی را اول commit می‌کند و دومی روی همان وضعیت به‌روز کار می‌کند. برای سناریوهای حساس‌تر می‌توان **optimistic locking** (مثلاً با فیلد version) یا **pessimistic lock** (SELECT FOR UPDATE) اضافه کرد؛ در کد فعلی ساده‌ترین حالت در نظر گرفته شده است.

---

### س: تفاوت Liveness و Readiness در health check چیست؟

**پاسخ:** **Liveness**: «آیا پروسس زنده است؟» — اگر جواب نه باشد، orchestrator (مثل Kubernetes) کانتینر را ریستارت می‌کند. در پروژه `GET /api/v1/health` فقط برمی‌گرداند که اپ جواب می‌دهد. **Readiness**: «آیا اپ آمادهٔ دریافت ترافیک است؟» — مثلاً اتصال به DB و Redis برقرار است. در پروژه `GET /api/v1/health/ready` فعلاً فقط یک پاسخ ثابت برمی‌گرداند؛ می‌توان آن را گسترش داد و واقعاً یک اتصال تست به DB یا Redis زد و در صورت شکست 503 برگرداند تا load balancer ترافیک را به این instance نفرستد.

---

با خواندن این سند و مراجعهٔ مستقیم به فایل‌ها و خطوط اشاره‌شده در پروژه، می‌توانید به پرسش‌های معمول مصاحبه در سطح Senior دربارهٔ معماری، دیزاین‌پترن، تکنولوژی‌ها و trade-offها پاسخ دقیق و مبتنی بر کد بدهید.
