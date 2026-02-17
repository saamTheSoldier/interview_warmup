# راهنمای بالا آوردن پروژه و بررسی کارکرد هر بخش

این سند مرحله‌به‌مرحله توضیح می‌دهد چطور سرویس‌ها را بالا بیاورید و **عملاً** چک کنید هر بخش چه کار می‌کند و درست کار می‌کند یا نه.

---

## پیش‌نیاز (یک بار)

- Python 3.12، venv، نصب وابستگی‌ها (`pip install -r requirements.txt`)
- PostgreSQL با کاربر `app` و دیتابیس `appdb` (مطابق `docs/RUN_WITHOUT_DOCKER.md`)
- Redis، RabbitMQ، Elasticsearch نصب و در حال اجرا
- فایل `.env` در روت پروژه با مقادیر درست

---

## ترتیب بالا آوردن سرویس‌ها

### ۱) سرویس‌های زیرساختی (قبل از API)

در ترمینال (در صورت نیاز با `sudo`):

```bash
sudo systemctl start postgresql
sudo systemctl start redis-server
sudo systemctl start rabbitmq-server
sudo systemctl start elasticsearch
```

**بررسی سریع:**

```bash
pg_isready -h localhost -p 5432
redis-cli ping
sudo rabbitmqctl status
curl -s 'http://localhost:9200/_cluster/health?pretty' | head -5
```

اگر هر چهار تا جواب درست دادند، ادامه بده.

---

### ۲) مایگریشن دیتابیس (فقط بار اول یا بعد از تغییر اسکیما)

```bash
cd /home/saam/work/interviews
source .venv/bin/activate
alembic upgrade head
```

خروجی باید شبیه: `Running upgrade ... -> 001, Initial schema: users and items`

---

### ۳) API (FastAPI)

```bash
cd /home/saam/work/interviews
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**چک کردن این بخش:**

| کار | انتظار | یعنی چه چیزی درست است؟ |
|-----|--------|-------------------------|
| باز کردن مرورگر: http://localhost:8000 | صفحهٔ Mini UI با «Health: OK» | API بالا آمده، endpoint سلامت جواب می‌دهد |
| کلیک روی «Load / Refresh list» (بدون لاگین) | لیست آیتم‌ها (خالی یا پر) | **PostgreSQL**: کوئری لیست آیتم‌ها از DB درست اجرا می‌شود |
| ثبت‌نام (Register) با یک ایمیل و پسورد | پیام «Registered. Now login.» | **PostgreSQL**: درج کاربر در جدول `users` |
| لاگین (Login) با همان ایمیل/پسورد | «Logged in. User ID …» | **JWT**: توکن ساخته و برگردانده می‌شود |
| بعد از لاگین، Add Item (عنوان + دکمه Add) | «Item created (ID …). Celery will index…» | **PostgreSQL** ذخیره آیتم، **Celery** تسک ایندکس در صف قرار می‌گیرد (اگر Worker روشن باشد ایندکس در ES هم انجام می‌شود) |
| Load / Refresh list دوباره | همان آیتم در لیست با ایمیل مالک | **Redis (اختیاری)**: برای آیتم تکی کش می‌شود؛ لیست از DB با **eager loading** (N+1 حل شده) |
| در کادر Search یک کلمه (مثلاً «لپ‌تاپ») و Search | لیست نتایج یا «No results» | **Elasticsearch**: جستجو روی ایندکس `items`؛ اگر Worker نزده باشد یا داده نباشد خالی است |

---

### ۴) Celery Worker (برای ایندکس شدن آیتم‌ها در Elasticsearch)

در **یک ترمینال جدید** (هم‌زمان با بالا بودن API):

```bash
cd /home/saam/work/interviews
source .venv/bin/activate
celery -A app.queue.celery_app worker --loglevel=info
```

**چک کردن این بخش:**

| کار | انتظار | یعنی چه چیزی درست است؟ |
|-----|--------|-------------------------|
| در لاگ Worker بعد از «Add Item» در UI | خطی شبیه `Task app.queue.tasks.index_item_task succeeded` | **RabbitMQ**: تسک از صف گرفته شد؛ **Celery** آن را اجرا کرد؛ **Elasticsearch**: ایندکس آیتم انجام شد |
| در UI دوباره Search با کلمهٔ همان آیتم | نتیجهٔ جستجو ظاهر می‌شود | **Elasticsearch** از طریق همین تسک پر شده و جستجو درست کار می‌کند |

اگر Worker را اصلاً بالا نیاوری، آیتم‌ها در DB و در لیست دیده می‌شوند ولی جستجو خالی می‌ماند (چون ایندکس در ES انجام نشده).

---

### ۵) اسکریپت دادهٔ حجیم (Seed)

وقتی **API** بالا است (و در صورت تمایل Worker هم بالا باشد):

```bash
cd /home/saam/work/interviews
source .venv/bin/activate
python scripts/seed_data.py
```

پیش‌فرض: ۳۰ کاربر و هر کدام ۲۵ آیتم (جمعاً ۷۵۰ آیتم). برای تعداد بیشتر:

```bash
python scripts/seed_data.py --users 100 --items-per-user 30
```

**چک کردن:**

| کار | انتظار | یعنی چه چیزی درست است؟ |
|-----|--------|-------------------------|
| خروجی اسکریپت | `Done. Users: 30, Items created: 750` (یا نزدیک به آن) | **PostgreSQL**: کاربران و آیتم‌ها از طریق API ساخته شدند؛ **RabbitMQ**: تسک‌های ایندکس در صف رفتند |
| در UI بعد از Load / Refresh list | لیست طولانی آیتم‌ها با pagination (۵۰ تا) | **PostgreSQL** دادهٔ حجیم را برمی‌گرداند؛ **Redis** برای آیتم تکی (وقتی روی یکی کلیک کنی یا بعداً get by id) کش می‌شود |
| در UI در Search بنویس «لپ‌تاپ» یا «کتاب» یا «Coffee» | چند نتیجه | **Elasticsearch** ایندکس پر شده (اگر Worker در حین/بعد از seed روشن بوده) |
| در Worker لاگ | تعداد زیاد `index_item_task succeeded` | **Celery + RabbitMQ** تسک‌ها را پردازش کرده‌اند |

---

## خلاصهٔ نقش هر بخش در UI و اسکریپت

| بخش | کجا استفاده می‌شود؟ | چطور ببینی کار می‌کند؟ |
|-----|---------------------|--------------------------|
| **PostgreSQL** | ذخیره کاربران و آیتم‌ها؛ لیست و جزئیات آیتم | Register، Login، Add Item، Load list؛ خروجی seed |
| **Redis** | کش جزئیات هر آیتم (کاهش بار DB) | بارها باز کردن همان آیتم یا همان درخواست get by id؛ پاسخ سریع‌تر بعد از بار اول |
| **RabbitMQ** | صف تسک‌های Celery | وقتی Add Item می‌زنی یا seed می‌زنی، تسک در صف قرار می‌گیرد؛ Worker آن را می‌گیرد |
| **Celery Worker** | اجرای تسک ایندکس در Elasticsearch | لاگ Worker: `index_item_task succeeded`؛ بعد Search نتیجه می‌دهد |
| **Elasticsearch** | جستجوی full-text روی آیتم‌ها | باکس Search در UI؛ نتایج فقط وقتی هست که Worker ایندکس را پر کرده باشد |
| **JWT / Auth** | لاگین و درخواست‌های محافظت‌شده | Login در UI؛ Add Item فقط بعد از لاگین |
| **Prometheus** | متریک‌های اپ | باز کردن http://localhost:8000/metrics و دیدن خروجی متنی |

---

## چک‌لیست سریع قبل از دمو یا مصاحبه

1. PostgreSQL، Redis، RabbitMQ، Elasticsearch: روشن و در دسترس
2. `alembic upgrade head` اجرا شده
3. API: `uvicorn app.main:app --port 8000` و در مرورگر http://localhost:8000 و Health: OK
4. (اختیاری) Celery Worker بالا تا جستجو پر از نتیجه باشد
5. (اختیاری) `python scripts/seed_data.py` برای دادهٔ حجیم
6. در UI: Register → Login → Add Item → Load list → Search و مشاهدهٔ نتیجه

با این مراحل می‌توانی در حین استفاده دقیقاً ببینی هر بخش (DB، کش، صف، Worker، جستجو، احراز هویت) چه می‌کند و آیا درست جواب می‌دهد یا نه.
