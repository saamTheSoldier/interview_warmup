# راه‌اندازی Elasticsearch (بدون Docker)

در نصب پیش‌فرض Elasticsearch 8، **HTTPS** و **احراز هویت** روشن است.

## اگر سرویس استارت نمی‌شود (خطای keystore / SSL)

اگر در لاگ خطایی شبیه این دیدی:
`cannot read configured [PKCS12] keystore ... (no password was provided)` یا `keystore password was incorrect`، یعنی تنظیمات به فایل‌های `http.p12` / `transport.p12` اشاره می‌کنند ولی پسورد keystore درست نیست. برای محیط توسعه می‌توانی **SSL را غیرفعال کنی و ارجاع به keystore را حذف کنی**:

1. پشتیبان از تنظیمات:  
   `sudo cp /etc/elasticsearch/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml.bak`

2. ویرایش `/etc/elasticsearch/elasticsearch.yml`: در بلوک‌های `xpack.security.http.ssl` و `xpack.security.transport.ssl` فقط `enabled: false` بگذار و خطوط **keystore.path** و **truststore.path** را حذف کن. مثلاً:

   ```yaml
   xpack.security.http.ssl:
     enabled: false
   # خط keystore.path را حذف کن

   xpack.security.transport.ssl:
     enabled: false
     verification_mode: certificate
   # خطوط keystore.path و truststore.path را حذف کن
   ```

3. ریستارت:  
   `sudo systemctl restart elasticsearch`

4. تست:  
   `curl -s 'http://localhost:9200/_cluster/health?pretty'`

--- بنابراین با `curl http://localhost:9200` پاسخی نمی‌گیری (اتصال با HTTP خالی برمی‌گردد) و با HTTPS هم بدون نام کاربری/رمز عبور خطای 401 می‌گیری.

دو راه داری:

---

## راه ۱: غیرفعال کردن امنیت (مناسب توسعهٔ محلی)

با غیرفعال کردن امنیت، Elasticsearch روی **HTTP** و **بدون پسورد** کار می‌کند و اپ با همان `http://localhost:9200` وصل می‌شود.

### مراحل (بعد از نصب ES 8)

1. **متوقف کردن Elasticsearch**
   ```bash
   sudo systemctl stop elasticsearch
   ```

2. **ویرایش تنظیمات**
   ```bash
   sudo nano /etc/elasticsearch/elasticsearch.yml
   ```
   این خطوط را **در انتهای فایل** اضافه کن:
   ```yaml
   xpack.security.enabled: false
   xpack.security.http.ssl.enabled: false
   xpack.security.transport.ssl.enabled: false
   ```

3. **حذف پسوردهای keystore** (الزامی برای خاموش ماندن امنیت بعد از یک بار روشن شدن)
   ```bash
   sudo /usr/share/elasticsearch/bin/elasticsearch-keystore list
   ```
   اگر خطوطی مثل زیر بود، آن‌ها را حذف کن (یکی یکی):
   ```bash
   sudo /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.keystore.secure_password
   sudo /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.truststore.secure_password
   sudo /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.http.ssl.keystore.secure_password
   ```
   (فقط همان‌هایی که با `list` دیدی را remove کن.)

4. **اجرای دوبارهٔ Elasticsearch**
   ```bash
   sudo systemctl start elasticsearch
   ```

5. **تست**
   ```bash
   curl -s http://localhost:9200/_cluster/health?pretty
   ```
   باید خروجی JSON با `"status" : "green"` یا `"yellow"` ببینی.

6. **تنظیم اپ**
   در `.env` همین کافی است (همان مقدار پیش‌فرض):
   ```env
   ELASTICSEARCH_URL=http://localhost:9200
   ```
   بعد API را یک بار ریستارت کن.

---

## راه ۲: نگه داشتن امنیت (HTTPS + نام کاربری/رمز عبور)

اگر امنیت را روشن نگه می‌داری، اپ باید با **HTTPS** و **Basic Auth** به Elasticsearch وصل شود.

### ۱) پیدا کردن پسورد کاربر `elastic`

در نصب اولیه، Elasticsearch یک رمز موقت برای کاربر `elastic` چاپ می‌کند یا در فایل می‌نویسد. یکی از این‌ها را امتحان کن:

```bash
sudo cat /etc/elasticsearch/elasticsearch.yml | grep -i password
sudo journalctl -u elasticsearch | grep -i password
```

اگر رمز را عوض کرده‌ای، همان رمز جدید را استفاده کن. در غیر این صورت می‌توانی رمز را با دستور زیر ریست کنی:

```bash
sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic -i
```
(یک رمز جدید وارد می‌کنی و تأیید می‌کنی.)

### ۲) تست اتصال با curl

```bash
curl -s -k -u elastic:YOUR_PASSWORD https://localhost:9200/_cluster/health?pretty
```
به‌جای `YOUR_PASSWORD` رمز کاربر `elastic` را بگذار. اگر خروجی JSON دیدی، اتصال درست است.

### ۳) تنظیم اپ

در `.env` آدرس را با **HTTPS** و **نام کاربری و رمز** بگذار:

```env
ELASTICSEARCH_URL=https://elastic:YOUR_PASSWORD@localhost:9200
ELASTICSEARCH_VERIFY_CERTS=false
```

- `YOUR_PASSWORD` را با رمز واقعی عوض کن.
- `ELASTICSEARCH_VERIFY_CERTS=false` برای گواهی خودامضای محلی است؛ در پروداکشن با گواهی معتبر معمولاً `true` می‌گذاری.

سپس API را ریستارت کن.

---

## جمع‌بندی

| حالت | ELASTICSEARCH_URL در `.env` | تست با curl |
|------|-----------------------------|-------------|
| امنیت خاموش (راه ۱) | `http://localhost:9200` | `curl http://localhost:9200/_cluster/health?pretty` |
| امنیت روشن (راه ۲) | `https://elastic:پسورد@localhost:9200` و `ELASTICSEARCH_VERIFY_CERTS=false` | `curl -k -u elastic:پسورد https://localhost:9200/_cluster/health?pretty` |

بعد از درست شدن اتصال، یک بار API را ریستارت کن تا ایندکس `items` ساخته شود و در صورت نیاز Celery Worker را هم اجرا کن تا آیتم‌ها ایندکس شوند.
