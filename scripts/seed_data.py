#!/usr/bin/env python3
"""
Seed script: creates many users and items via the API (no direct DB).
Ensures: PostgreSQL has data, Celery tasks are queued, Elasticsearch gets indexed when worker runs.
Run: API must be running. For ES indexing, run Celery worker as well.
  python scripts/seed_data.py
  python scripts/seed_data.py --users 100 --items-per-user 30
"""

import argparse
import random
import sys
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

API_BASE = "http://localhost:8000/api/v1"

# Realistic titles/descriptions for search and UI (mixed EN/FA)
TITLES = [
    "لپ‌تاپ ایسوس", "MacBook Pro", "کیبورد مکانیکی", "ماوس بی‌سیم", "هدفون بلوتوث",
    "مانیتور ۲۷ اینچ", "وب‌کم HD", "اسپیکر بلوتوث", "شارژر موبایل", "کابل USB-C",
    "Laptop stand", "دستگاه تصفیه آب", "قهوه ساز", "چرخ خیاطی", "مخلوط کن",
    "کتاب برنامه‌نویسی پایتون", "کتاب طراحی وب", "دوره آنلاین React", "موسیک باکس",
    "ساعت هوشمند", "تبلت سامسونگ", "گوشی شیائومی", "پاوربانک", "هارد اکسترنال",
    "فلش ۶۴ گیگ", "کارت حافظه", "آداپتور چند پورت", "لایتینگ یواس بی", "پایه موبایل",
    "Coffee maker", "Electric kettle", "Toaster", "Blender", "Air fryer",
    "کوله پشتی", "کیف لپ‌تاپ", "قلم نوری", "تبلت گرافیکی", "میکروفون یواس بی",
    "Ring light", "Tripod", "Green screen", "Streaming mic", "Webcam 4K",
]

DESCRIPTIONS = [
    "مناسب برای کار و تحصیل. کیفیت عالی و گارانتی.",
    "سازگار با ویندوز و مک. طراحی سبک و مقاوم.",
    "برای توسعه‌دهندگان و علاقه‌مندان به تکنولوژی.",
    "ارگونومیک و راحت برای استفاده طولانی مدت.",
    "با باتری با دوام و شارژ سریع.",
    "مناسب برای استریم و کنفرانس آنلاین.",
    "Great for home office and remote work.",
    "High quality build and reliable performance.",
    "Popular choice for developers and designers.",
    "با گارانتی ۱۸ ماهه و پشتیبانی فارسی.",
]


def random_title() -> str:
    return random.choice(TITLES) + (" " + str(random.randint(1, 999)) if random.random() > 0.5 else "")


def random_description() -> str:
    return random.choice(DESCRIPTIONS)


def random_price() -> int:
    return random.choice([0, 99, 199, 499, 999, 1999, 4999, 9999, 19999, 49999])


def main():
    ap = argparse.ArgumentParser(description="Seed users and items via API")
    ap.add_argument("--users", type=int, default=30, help="Number of users to create")
    ap.add_argument("--items-per-user", type=int, default=25, help="Items per user")
    ap.add_argument("--base-url", default=API_BASE, help="API base URL")
    args = ap.parse_args()

    created_users = []
    created_items = 0
    errors = []

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        # 1) Create users
        print(f"Creating {args.users} users...")
        for i in range(args.users):
            email = f"user{i+1}@example.com"
            password = "password123"
            full_name = f"User {i+1}"
            try:
                r = client.post("/users/register", json={
                    "email": email,
                    "password": password,
                    "full_name": full_name,
                })
                if r.status_code in (200, 201):
                    created_users.append({"email": email, "password": password, "id": r.json().get("id")})
                elif r.status_code == 409:
                    # Already exists - we'll use same creds for login
                    created_users.append({"email": email, "password": password, "id": i + 1})
                else:
                    errors.append(f"Register {email}: {r.status_code} {r.text[:80]}")
            except Exception as e:
                errors.append(f"Register {email}: {e}")
            if (i + 1) % 10 == 0:
                print(f"  ... {i+1} users")

        # 2) Login and create items per user
        print(f"Creating ~{len(created_users) * args.items_per_user} items (login + POST)...")
        for u in created_users:
            try:
                r = client.post("/users/login", json={"email": u["email"], "password": u["password"]})
                if r.status_code != 200:
                    errors.append(f"Login {u['email']}: {r.status_code}")
                    continue
                token = r.json().get("access_token")
                user_id = r.json().get("user_id") or u.get("id")
                if not token:
                    continue
                headers = {"Authorization": f"Bearer {token}"}
                for _ in range(args.items_per_user):
                    try:
                        r2 = client.post(
                            "/items",
                            headers=headers,
                            json={
                                "title": random_title(),
                                "description": random_description(),
                                "price_cents": random_price(),
                                "owner_id": user_id,
                            },
                        )
                        if r2.status_code in (200, 201):
                            created_items += 1
                        else:
                            errors.append(f"Item {u['email']}: {r2.status_code}")
                    except Exception as e:
                        errors.append(str(e))
            except Exception as e:
                errors.append(f"User {u['email']}: {e}")
            if len(created_users) <= 10 or created_users.index(u) % 5 == 0:
                print(f"  User {u['email']}: +{args.items_per_user} items (total items so far: {created_items})")

    print(f"\nDone. Users: {len(created_users)}, Items created: {created_items}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors[:15]:
            print("  ", e)
        if len(errors) > 15:
            print("  ... and", len(errors) - 15, "more")
    print("\nTip: Run Celery worker to index items in Elasticsearch, then use Search in the UI.")


if __name__ == "__main__":
    main()
