# راه‌اندازی پروژه بدون Docker (بدون داکر)

این سند تمام مراحل لازم برای اجرای پروژه **بدون Docker** روی سیستم محلی (Linux) را شرح می‌دهد: نصب نیازمندی‌ها، بالا آوردن سرویس‌ها، تنظیم دیتابیس، و اجرای API و Celery Worker.

---

## پیش‌نیاز

- **Python 3.12** (یا 3.10+)
- دسترسی **sudo** برای نصب PostgreSQL، Redis، RabbitMQ (و در صورت تمایل Elasticsearch)
- اتصال اینترنت برای نصب پکیج‌ها

---

## خلاصهٔ مراحل

1. نصب وابستگی‌های Python (venv + pip)
2. نصب و راه‌اندازی PostgreSQL و ایجاد کاربر/دیتابیس
3. نصب و راه‌اندازی Redis
4. نصب و راه‌اندازی RabbitMQ
5. (اختیاری) نصب و راه‌اندازی Elasticsearch
6. ایجاد فایل `.env`
7. اجرای مایگریشن دیتابیس (Alembic)
8. اجرای API (Uvicorn)
9. (اختیاری) اجرای Celery Worker

---

## 1. نصب وابستگی‌های Python

در روت پروژه:

```bash
cd /home/saam/work/interviews

# ساخت محیط مجازی
python3 -m venv .venv

# فعال‌سازی (در هر ترمینال جدید)
source .venv/bin/activate   # Linux/macOS

# به‌روزرسانی pip و نصب نیازمندی‌ها
pip install --upgrade pip
pip install -r requirements.txt
```

اگر خطای `email-validator` یا `ModuleNotFoundError: No module named 'email_validator'` دیدید:

```bash
pip install email-validator
```

یا مطمئن شوید `pydantic[email-validator]` و در صورت نیاز پکیج صریح `email-validator` در `requirements.txt` هست و دوباره `pip install -r requirements.txt` بزنید.

**بررسی نصب:**

```bash
.venv/bin/python -c "import fastapi, uvicorn, sqlalchemy, asyncpg, redis, celery; print('OK')"
```

---

## 2. PostgreSQL

### نصب (در صورت نبود)

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### ایجاد کاربر و دیتابیس

پروژه انتظار دارد کاربر `app` با پسورد `secret` و دیتابیس `appdb` وجود داشته باشد (مطابق `app/config.py` و `.env.example`).

```bash
sudo -u postgres psql << 'EOF'
CREATE USER app WITH PASSWORD 'secret';
CREATE DATABASE appdb OWNER app;
\q
EOF
```

**بررسی:**

```bash
pg_isready -h localhost -p 5432
psql -h localhost -U app -d appdb -c "SELECT 1;"   # پسورد: secret
```

---

## 3. Redis

### نصب

```bash
sudo apt-get update
sudo apt-get install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**بررسی:**

```bash
redis-cli ping
# باید پاسخ PONG برگردد.
```

پورت پیش‌فرض: **6379**.

---

## 4. RabbitMQ

### نصب

RabbitMQ به Erlang وابسته است؛ بسته‌های لازم معمولاً با `rabbitmq-server` نصب می‌شوند.

```bash
sudo apt-get update
sudo apt-get install -y rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
```

**بررسی:**

```bash
sudo rabbitmqctl status
```

پورت پیش‌فرض AMQP: **5672**. پورت مدیریت (در صورت نصب پلاگین management): **15672**.

کاربر پیش‌فرض: `guest` / `guest` (فقط از localhost).

---

## 5. Elasticsearch (اختیاری)

اپ بدون Elasticsearch هم بالا می‌آید؛ جستجو در آن صورت خالی برمی‌گردد (Graceful Degradation). برای جستجوی واقعی باید Elasticsearch را نصب و اجرا کنید.

### نصب (مثال برای Ubuntu/Debian)

```bash
# نصب Java (الزامی برای Elasticsearch)
sudo apt-get install -y openjdk-17-jdk

# اضافه کردن مخزن Elastic (مطابق مستندات رسمی Elastic)
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt-get update
sudo apt-get install -y elasticsearch

# اجرا
sudo systemctl start elasticsearch
sudo systemctl enable elasticsearch
```

تنظیمات تک‌نود (برای توسعه): در `/etc/elasticsearch/elasticsearch.yml` می‌توانید `discovery.type: single-node` و در صورت نیاز `xpack.security.enabled: false` قرار دهید.

**بررسی:**

```bash
curl -s http://localhost:9200/_cluster/health?pretty
```

پورت پیش‌فرض: **9200**.

---

## 6. فایل `.env`

در روت پروژه یک فایل `.env` بسازید (می‌توانید از `.env.example` کپی کنید):

```bash
cp .env.example .env
```

مقادیر پیش‌فرض برای اجرای محلی (بدون Docker):

```env
SECRET_KEY=dev-secret-change-in-production
DATABASE_URL=postgresql+asyncpg://app:secret@localhost:5432/appdb
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URL=http://localhost:9200
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
```

در صورت استفاده از کاربر/پسورد یا پورت متفاوت برای PostgreSQL، Redis یا RabbitMQ، همین متغیرها را در `.env` اصلاح کنید.

---

## 7. مایگریشن دیتابیس (Alembic)

یک بار (و بعد از هر تغییر اسکیما) مایگریشن را اجرا کنید:

```bash
cd /home/saam/work/interviews
source .venv/bin/activate
alembic upgrade head
```

خروجی موفق شبیه این است:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema: users and items
```

---

## 8. اجرای API (Uvicorn)

در یک ترمینال:

```bash
cd /home/saam/work/interviews
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **با reload**: برای توسعه؛ با هر تغییر کد سرور دوباره لود می‌شود.
- **بدون reload (پروداکشن)**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

**بررسی:**

- مستندات Swagger: http://localhost:8000/docs  
- سلامت: http://localhost:8000/api/v1/health  
- متریک Prometheus: http://localhost:8000/metrics  

اگر Elasticsearch بالا نباشد، اپ به‌صورت پیش‌فرض با `try/except` در lifespan خطای ES را نادیده می‌گیرد و بالا می‌آید؛ جستجو در آن صورت خالی برمی‌گردد.

---

## 9. اجرای Celery Worker (اختیاری)

برای پردازش تسک‌های صف (مثل ایندکس کردن آیتم در Elasticsearch)، در **ترمینال دوم**:

```bash
cd /home/saam/work/interviews
source .venv/bin/activate
celery -A app.queue.celery_app worker --loglevel=info
```

مطمئن شوید RabbitMQ در حال اجرا است و `CELERY_BROKER_URL` در `.env` درست است.

---

## خلاصهٔ دستورات یک‌جا (کپی/پیست)

فرض: پروژه در `/home/saam/work/interviews` و شما در همان پوشه هستید.

```bash
# 1) Python
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install email-validator   # در صورت نیاز

# 2) PostgreSQL (با دسترسی sudo)
sudo -u postgres psql -c "CREATE USER app WITH PASSWORD 'secret';"
sudo -u postgres psql -c "CREATE DATABASE appdb OWNER app;"

# 3) Redis
sudo apt-get install -y redis-server && sudo systemctl start redis-server
redis-cli ping

# 4) RabbitMQ
sudo apt-get install -y rabbitmq-server && sudo systemctl start rabbitmq-server
sudo rabbitmqctl status

# 5) .env
cp .env.example .env
# در صورت نیاز .env را ویرایش کنید.

# 6) مایگریشن
alembic upgrade head

# 7) اجرای API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

در ترمینال دیگر برای Worker:

```bash
source .venv/bin/activate
celery -A app.queue.celery_app worker --loglevel=info
```

---

## عیب‌یابی

| مشکل | اقدام |
|------|--------|
| `ModuleNotFoundError: email_validator` | `pip install email-validator` |
| اتصال به PostgreSQL رد می‌شود | بررسی روشن بودن سرویس: `sudo systemctl status postgresql`؛ بررسی کاربر/پسورد و `DATABASE_URL` در `.env` |
| اتصال به Redis رد می‌شود | `redis-cli ping` و `sudo systemctl start redis-server` |
| Celery به صف وصل نمی‌شود | بررسی RabbitMQ: `sudo rabbitmqctl status` و `CELERY_BROKER_URL` |
| خطای Elasticsearch در startup | Elasticsearch را بالا بیاورید یا فراخوانی `ensure_items_index()` در lifespan را در try/except قرار دهید |
| پورت 8000 اشغال است | پورت دیگر: `uvicorn app.main:app --port 8001` |

---

## وضعیت انجام‌شده در این محیط

- ✅ PostgreSQL: نصب و در حال اجرا؛ کاربر `app` و دیتابیس `appdb` ساخته شده‌اند.
- ✅ Redis: نصب و در حال اجرا؛ `redis-cli ping` پاسخ PONG می‌دهد.
- ✅ RabbitMQ: نصب و در حال اجرا.
- ✅ محیط مجازی Python (`.venv`) و نصب پکیج‌ها از `requirements.txt`.
- ✅ فایل `.env` ایجاد شده است.
- ✅ مایگریشن با `alembic upgrade head` اجرا شده است.
- ⚠️ Elasticsearch: اختیاری؛ در این راهنما به‌صورت دستی و در بخش اختیاری توضیح داده شده است.
- ⚠️ برای بالا آمدن بدون خطای اپ، حتماً `email-validator` نصب باشد (`pip install email-validator` یا نصب کامل `requirements.txt`).

با انجام این مراحل، پروژه بدون Docker روی ماشین محلی شما قابل اجرا است.
