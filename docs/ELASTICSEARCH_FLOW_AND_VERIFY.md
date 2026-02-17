# جریان ایندکس و جستجو در Elasticsearch + نحوهٔ تأیید

## فرآیند به طور کلی

1. **ساخت آیتم (API)**  
   وقتی با `POST /api/v1/items` یک آیتم می‌سازی، در دیتابیس (PostgreSQL) ذخیره می‌شود و **فقط یک تسک به صف Celery (RabbitMQ) فرستاده می‌شود**. خود API مستقیم چیزی داخل Elasticsearch نمی‌نویسد.

2. **ذخیره در Elasticsearch (Celery Worker)**  
   **فقط Celery worker** داکیومنت‌ها را در Elasticsearch ایندکس می‌کند:
   - Worker تسک `index_item_task` را از RabbitMQ می‌گیرد.
   - داخل تسک، `index_item_sync()` با کلاینت sync به ES وصل می‌شود و همان آیتم را در ایندکس `items` می‌نویسد.

3. **جستجو (API)**  
   وقتی `GET /api/v1/search/items?q=...` را صدا می‌زنی، API مستقیم از Elasticsearch با `search_items()` جستجو می‌کند و نتیجه را برمی‌گرداند.

**خلاصه:**  
- **کی ذخیره می‌کند؟** فقط **Celery worker** (با تسک `index_item_task`).  
- اگر worker روشن نباشد یا تسک خطا بدهد، ایندکس `items` خالی یا ناقص می‌ماند و جستجو نتیجه نمی‌دهد.

---

## از کجا بفهمیم واقعاً توی Elasticsearch ذخیره شده؟

با **curl** مستقیم روی Elasticsearch چک کن:

### ۱. تعداد داکیومنت‌های ایندکس `items`

```bash
curl -s 'http://localhost:9200/items/_count?pretty'
```

خروجی نمونه:
```json
{
  "count" : 750
}
```
اگر `count` صفر است، یعنی هیچ داکیومنتی ایندکس نشده (یا worker اجرا نشده / تسک‌ها خطا می‌دهند).

### ۲. چند تا داکیومنت نمونه از ایندکس

```bash
curl -s 'http://localhost:9200/items/_search?size=5&pretty'
```

اگر ایندکس پر باشد، لیستی از `_source` (عنوان، توضیح، و ...) می‌بینی.

### ۳. لیست ایندکس‌ها

```bash
curl -s 'http://localhost:9200/_cat/indices?v'
```

باید ایندکس `items` را در لیست ببینی.

---

## خطای ۵۰۳ و `no_shard_available_action_exception`

در کلاستر **تک‌نود**، پیش‌فرض Elasticsearch این است که هر ایندکس یک **replica** داشته باشد. replica روی همان نود قرار نمی‌گیرد، پس شارد replica «unassigned» می‌ماند و گاهی جستجو/شمارش با خطای `all shards failed` و وضعیت ۵۰۳ مواجه می‌شود.

**رفع برای ایندکس فعلی:**

اگر بعد از تنظیم `number_of_replicas: 0` هنوز خطای ۵۰۳ و `no_shard_available` می‌گیری، یعنی شارد ایندکس در وضعیت خراب مانده. در این حالت ایندکس را **حذف** کن و دوباره پر کن.

**راه ساده (یک دستور):** اسکریپت reindex با پرچم `--reset-index` اول ایندکس را حذف می‌کند، بعد همهٔ آیتم‌ها را به صف می‌فرستد؛ Celery ایندکس را از نو با `number_of_replicas: 0` می‌سازد و پر می‌کند:

```bash
# Celery worker باید روشن باشد (در یک ترمینال جدا)
python scripts/reindex_elasticsearch.py --reset-index
```

بعد از چند ثانیه تست کن:  
`curl -s 'http://localhost:9200/items/_count?pretty'`

**راه دستی:** اول ایندکس را حذف کن، بعد reindex بدون پرچم:

```bash
curl -X DELETE "http://localhost:9200/items"
python scripts/reindex_elasticsearch.py
```

اگر فقط می‌خواهی replica را عوض کنی و ایندکس سالم است، این کافی است (و بعد از آن دیگر ۵۰۳ نبینی):

```bash
curl -X PUT "http://localhost:9200/items/_settings" -H "Content-Type: application/json" -d '{"index":{"number_of_replicas":0}}'
```

از این به بعد در کد، هنگام **ساخت** ایندکس `items` (توسط API یا Celery)، `number_of_replicas: 0` تنظیم می‌شود تا در تک‌نود این مشکل پیش نیاید.

---

## اگر هنوز ۵۰۳ می‌گیری (شارد assign نمی‌شود)

گاهی حتی با حذف و ساخت مجدد، ایندکس باز هم `no_shard_available` می‌دهد. در این حالت یا درخواست ساخت از طرف کلاینت درست نمی‌رسد، یا **تنظیمات کلاستر** Elasticsearch مانع assign شدن شارد است.

### ۱. تشخیص: چرا شارد assign نشده؟

این دستورات را اجرا کن و خروجی را ببین:

```bash
# وضعیت کلاستر (green/yellow/red)
curl -s 'http://localhost:9200/_cluster/health?pretty'

# وضعیت شاردهای ایندکس items
curl -s 'http://localhost:9200/_cat/shards/items?v'

# دلیل عدم assign (دقیق‌تر)
curl -s -X POST 'http://localhost:9200/_cluster/allocation/explain?pretty' \
  -H 'Content-Type: application/json' \
  -d '{"index":"items","shard":0,"primary":true}'
```

اگر در `allocation/explain` دلیلی مثل **disk watermark** یا **filtering** دیدی، باید آن را در تنظیمات ES یا فضای دیسک برطرف کنی.

### اگر دلیل «disk_threshold» بود (دیسک پر)

پیام شبیه این است:  
`the node is above the high watermark cluster setting [cluster.routing.allocation.disk.watermark.high=90%], having less than the minimum required [...] free space, actual free: [53.6gb], actual used: [94.1%]`

یعنی استفاده از دیسک از حد مجاز (پیش‌فرض ۹۰٪) بیشتر شده و Elasticsearch عمداً شارد assign نمی‌کند.

**راه‌حل ۱ (بهتر):** فضای دیسک را آزاد کن تا استفاده زیر ۹۰٪ (یا زیر حدی که در تنظیمات داری) برود.

**راه‌حل ۲ (موقت، فقط توسعه):** اگر در محیط توسعه هستی و می‌خواهی موقتاً شارد assign شود، watermark را بالاتر ببر (مثلاً ۹۸٪):

```bash
curl -X PUT "http://localhost:9200/_cluster/settings?pretty" -H "Content-Type: application/json" -d '{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "95%",
    "cluster.routing.allocation.disk.watermark.high": "98%",
    "cluster.routing.allocation.disk.watermark.flood_stage": "99%"
  }
}'
```

بعد از آن، شاردها باید assign شوند (ممکن است چند ثانیه طول بکشد). دوباره تست کن:  
`curl -s 'http://localhost:9200/items/_count?pretty'`

### ۲. ساخت ایندکس با HTTP خام (بدون کلاینت پایتون)

یک بار ایندکس را با اسکریپتی که مستقیم REST می‌زند بساز، بعد فقط reindex بزن (بدون حذف ایندکس):

```bash
# حذف ایندکس قبلی
curl -X DELETE "http://localhost:9200/items"

# ساخت ایندکس با بدنهٔ ثابت (number_of_replicas=0)
python scripts/create_es_items_index.py

# پر کردن با Celery (worker باید روشن باشد؛ بدون --reset-index)
python scripts/reindex_elasticsearch.py
```

بعد از چند ثانیه:  
`curl -s 'http://localhost:9200/items/_count?pretty'`

اگر باز ۵۰۳ بود، مشکل از **کلاستر** است (مثلاً دیسک، یا تنظیم allocation). خروجی `_cluster/allocation/explain` را چک کن.

---

## اگر جستجو همیشه خالی است

1. **Celery worker را اجرا کن** (در یک ترمینال جدا):
   ```bash
   celery -A app.queue.celery_app worker --loglevel=info
   ```

2. **تسک‌های قدیمی را یکجا اجرا کن (reindex):**
   ```bash
   python scripts/reindex_elasticsearch.py
   ```
   این اسکریپت آیتم‌های دیتابیس را صفحه‌به‌صفحه می‌خواند و برای هر کدام تسک ایندکس به صف می‌فرستد؛ worker آن‌ها را در ES می‌نویسد.

3. **لاگ worker را ببین:**  
   اگر `index_item_sync failed for doc id=...` یا `Index failed` دیدی، یعنی ایندکس شدن خطا می‌دهد و باید آن خطا را برطرف کنی.

4. **لاگ API:**  
   بعد از اضافه کردن لاگ، اگر ایندکس خالی باشد در لاگ Uvicorn می‌بینی:  
   `search_items: query='...' returned 0 hits (index may be empty or Celery not indexing)`.

---

## خلاصه جریان

```
[کاربر]  POST /api/v1/items
    → API: ذخیره در PostgreSQL + ارسال تسک به RabbitMQ
    → Celery Worker: index_item_task → index_item_sync() → نوشتن در ES (ایندکس "items")

[کاربر]  GET /api/v1/search/items?q=...
    → API: search_items() → خواندن از همان ایندکس "items" در ES
```

اگر worker روشن نباشد یا تسک‌ها fail شوند، ایندکس خالی می‌ماند و جستجو همیشه ۰ نتیجه برمی‌گرداند.

---

## Celery چیست و این دستور چه کار می‌کند؟

**Celery** یک صف تسک (task queue) است: کارهای سنگین یا زمان‌بر را از مسیر درخواست HTTP جدا می‌کند. به‌جای اینکه API خودش مستقیم Elasticsearch را صدا بزند (و کاربر منتظر بماند)، فقط یک «تسک» را به یک **بروکر** (مثلاً RabbitMQ) می‌فرستد و جواب را فوراً به کاربر می‌دهد. یک پروسهٔ جدا (**worker**) تسک‌ها را از صف می‌گیرد و اجرا می‌کند (مثلاً ایندکس کردن در ES).

- **بروکر (Broker):** RabbitMQ — صفی که تسک‌ها روی آن قرار می‌گیرند.
- **Worker:** پروسه‌ای که این دستور آن را اجرا می‌کند و تسک‌ها را یکی‌یکی (یا چندتایی موازی) انجام می‌دهد.

**معنی دستور:**

```bash
celery -A app.queue.celery_app worker --loglevel=info
```

| بخش | معنی |
|-----|------|
| `celery` | اجرای برنامهٔ Celery |
| `-A app.queue.celery_app` | **اپ Celery** کجاست: ماژول `app.queue.celery_app` (همان جایی که `celery_app = Celery(...)` و تنظیمات و لیست تسک‌ها تعریف شده). |
| `worker` | این پروسه یک **worker** باشد؛ یعنی تسک‌ها را از صف بخواند و اجرا کند (نه beat، نه shell). |
| `--loglevel=info` | سطح لاگ: `info` تا ببینی تسک‌ها کی دریافت و اجرا و retry می‌شوند. |

خلاصه: این دستور یک worker Celery را روشن می‌کند که به RabbitMQ وصل می‌شود و تسک‌هایی مثل `index_item_task` را اجرا می‌کند (از جمله نوشتن در Elasticsearch).

---

## اگر خطای «Connection timed out» دیدی

در لاگ worker اگر `index_item_sync failed ... Connection timed out` و `PUT http://localhost:9200/items/_doc/... [status:N/A duration:10.010s]` دیدی، یعنی درخواست **PUT** به Elasticsearch قبل از رسیدن پاسخ، بعد از حدود ۱۰ ثانیه قطع شده. معمولاً **HEAD** همان آدرس با ۲۰۰ جواب می‌دهد، ولی وقتی چند worker هم‌زمان چند PUT می‌فرستند، ES یا شبکه کند می‌شود و timeout پیش‌فرض کم است.

**کارهای انجام‌شده در کد:** برای کلاینت Elasticsearch یک **request_timeout** بزرگ‌تر (۳۰ ثانیه) گذاشته شده تا PUTها فرصت بیشتری برای جواب داشته باشند.

**اگر باز timeout خوردی:** می‌توانی تعداد workerهای موازی را کم کنی تا فشار روی ES کمتر شود:

```bash
celery -A app.queue.celery_app worker --loglevel=info --concurrency=2
```

با `--concurrency=2` فقط ۲ worker هم‌زمان تسک می‌گیرند (به‌جای تعداد پیش‌فرض که معمولاً برابر هسته‌های CPU است).
