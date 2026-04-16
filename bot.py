import requests
import random
import time
import os
from datetime import datetime

# ══════════════════════════════════════
#  НАСТРОЙКИ
# ══════════════════════════════════════
JAP_API_KEY   = "ec2fb6c8f5a4ea7ba6cf532e87a09895"
JAP_API_URL   = "https://justanotherpanel.com/api/v2"
JAP_SERVICE   = 9604
QUANTITY_MIN  = 500
QUANTITY_MAX  = 1000

APIFY_TOKEN   = "apify_api_GQnmhAbG7jgFdjw0SYh6APbtpZgkek0W7GCA"
FB_PAGE_URL   = "https://www.facebook.com/profile.php?id=100081997113052"

CHECK_INTERVAL = 300  # проверять каждые 5 минут
STATE_FILE     = "last_post_id.txt"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def load_last_post_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            val = f.read().strip()
            return val if val else None
    return None

def save_last_post_id(post_id):
    with open(STATE_FILE, "w") as f:
        f.write(str(post_id))

def get_latest_post():
    """Получаем последний пост через Apify Facebook Posts Scraper"""
    try:
        ACTOR_ID = "KoJrdxJCTtpon81KY"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {APIFY_TOKEN}",
        }

        # Запускаем актор и ждём результат синхронно
        log("📤 Запускаю Apify Facebook Posts Scraper...")
        run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
        payload = {
            "startUrls": [{"url": FB_PAGE_URL}],
            "resultsLimit": 20,
            "scrapePostsUntilDate": "",
        }
        resp = requests.post(
            run_url,
            json=payload,
            headers=headers,
            timeout=120,
            params={"token": APIFY_TOKEN}
        )
        log(f"📥 Apify: {resp.status_code}")

        if resp.status_code not in [200, 201]:
            log(f"❌ Ошибка: {resp.text[:300]}")
            return None, None, []

        try:
            data = resp.json()
        except Exception:
            log(f"❌ Ошибка парсинга JSON: {resp.text[:200]}")
            return None, None, []

        # Apify возвращает список постов напрямую
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items", [data])
        else:
            items = []

        log(f"📊 Найдено постов: {len(items)}")

        if not items:
            log("⚠️  Посты не найдены")
            return None, None, []

        # Сортируем по timestamp чтобы взять самый свежий
        def get_ts(item):
            return item.get("timestamp", 0) or 0
        items_sorted = sorted(items, key=get_ts, reverse=True)
        latest = items_sorted[0]

        post_id = latest.get("postId") or latest.get("id") or str(latest.get("timestamp", ""))
        post_url = latest.get("url") or latest.get("postUrl") or FB_PAGE_URL

        log(f"✅ Последний пост: {post_url} | postId: {post_id} | time: {latest.get('time', '')}")
        return str(post_id), post_url, items_sorted

    except Exception as e:
        log(f"❌ Ошибка Apify: {e}")
        return None, None, []

def create_jap_order(post_url):
    quantity = random.randint(QUANTITY_MIN, QUANTITY_MAX)
    payload = {
        "key":      JAP_API_KEY,
        "action":   "add",
        "service":  JAP_SERVICE,
        "link":     post_url,
        "quantity": quantity,
    }
    try:
        log(f"📤 Заказ JAP: service={JAP_SERVICE}, qty={quantity}")
        resp = requests.post(JAP_API_URL, data=payload, timeout=15)
        log(f"📥 JAP: {resp.status_code} | {repr(resp.text[:200])}")
        if not resp.text.strip():
            log("❌ Пустой ответ JAP")
            return
        data = resp.json()
        if "order" in data:
            log(f"✅ Заказ создан! ID: {data['order']} | Услуга: {JAP_SERVICE} | Кол-во: {quantity}")
        elif "error" in data:
            log(f"❌ Ошибка JAP: {data['error']}")
    except Exception as e:
        log(f"❌ Ошибка заказа: {e}")

def check_balance():
    try:
        resp = requests.post(JAP_API_URL, data={"key": JAP_API_KEY, "action": "balance"}, timeout=10)
        if resp.text.strip():
            data = resp.json()
            if "balance" in data:
                log(f"💰 Баланс JAP: ${data['balance']} {data.get('currency','')}")
    except Exception as e:
        log(f"❌ Ошибка баланса: {e}")

def main():
    log("🚀 Facebook бот запущен (через Apify)!")
    log(f"📘 Страница: {FB_PAGE_URL}")
    log(f"⚙️  Услуга: {JAP_SERVICE} | Кол-во: {QUANTITY_MIN}-{QUANTITY_MAX}")
    log(f"🔄 Проверка каждые {CHECK_INTERVAL//60} минут")
    check_balance()

    last_id = load_last_post_id()

    if not last_id:
        latest_id, _, _ = get_latest_post()
        if latest_id:
            save_last_post_id(latest_id)
            last_id = latest_id
            log(f"📌 Первый запуск. Последний пост: #{latest_id}. Жду новые...")

    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            latest_id, post_url, all_posts = get_latest_post()
            if latest_id and latest_id != last_id and all_posts:
                # Find all posts newer than last known
                new_posts = []
                for post in all_posts:
                    pid = str(post.get("postId") or post.get("id") or "")
                    pts = post.get("timestamp", 0) or 0
                    if pid and pid != last_id and pts > 0:
                        new_posts.append(post)
                
                if not new_posts:
                    new_posts = [all_posts[0]]
                
                log(f"🆕 Найдено новых постов: {len(new_posts)}")
                for post in new_posts:
                    purl = post.get("url") or post.get("postUrl") or FB_PAGE_URL
                    log(f"🆕 Обрабатываю пост: {purl}")
                    create_jap_order(purl)
                    time.sleep(3)
                
                save_last_post_id(latest_id)
                last_id = latest_id
            else:
                log(f"🔍 Нет новых постов (последний: #{last_id})")
        except Exception as e:
            log(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
