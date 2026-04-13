import requests
import random
import time
import os
import re
from datetime import datetime

JAP_API_KEY    = "ec2fb6c8f5a4ea7ba6cf532e87a09895"
JAP_API_URL    = "https://justanotherpanel.com/api/v2"
JAP_SERVICE    = 9604
QUANTITY_MIN   = 800
QUANTITY_MAX   = 1500
FB_PAGE_ID     = "100081997113052"
CHECK_INTERVAL = 60
STATE_FILE     = "last_post_id.txt"

C_USER = "61553351803414"
XS     = "8%3AeGYkn8717BMe-g%3A2%3A1774503965%3A-1%3A-1%3A%3AAcx7QLCab5zvbi-lFeNFfZQcV-306iuKpPhQ-CMII9A"
DATR   = "gvGqaR00HB8BBQCtWvA_ZrBw"
FR     = "1OB7RBWOZkX1xBj3q.AWdGZvbe7aj44os6vwRpRCJ_yyTD61uZlfP5i6ymIVp0HkEp4Ck.Bp3GP7..AAA.0.0.Bp3GP7.AWfFHkYvPlNCbCa6-PGu_kEQVWs"
SB     = "hfGqaZIWmBX2PQV9iqh9Tr1V"
WD     = "754x719"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": f"c_user={C_USER}; xs={XS}; datr={DATR}; fr={FR}; sb={SB}; wd={WD}",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Referer": "https://www.facebook.com/",
}

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
    try:
        url = f"https://www.facebook.com/profile.php?id={FB_PAGE_ID}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        log(f"📥 Facebook: {resp.status_code}")

        if resp.status_code != 200:
            log(f"⚠️  Ошибка: {resp.status_code}")
            return None, None

        # Decode content properly
        try:
            html = resp.content.decode("utf-8")
        except Exception:
            html = resp.text

        # Pattern 1: pfbid format
        matches = re.findall(r'pfbid[A-Za-z0-9]+', html)
        # Pattern 2: story_fbid
        matches2 = re.findall(r'"story_fbid":"(\d+)"', html)
        # Pattern 3: post_id
        matches3 = re.findall(r'"post_id":"(\d+)"', html)
        # Pattern 4: /posts/ID
        matches4 = re.findall(r'/posts/(\d+)', html)
        # Pattern 5: top_level_post_id
        matches5 = re.findall(r'"top_level_post_id":"(\d+)"', html)

        all_ids = list(set(matches2 + matches3 + matches4 + matches5))

        if matches:
            latest_pfbid = matches[0]
            post_url = f"https://www.facebook.com/permalink.php?story_fbid={latest_pfbid}&id={FB_PAGE_ID}"
            log(f"✅ Найден пост (pfbid): {post_url}")
            return latest_pfbid, post_url

        if all_ids:
            numeric = [x for x in all_ids if x.isdigit() and len(x) > 10]
            if numeric:
                latest_id = max(numeric, key=lambda x: int(x))
                post_url = f"https://www.facebook.com/permalink.php?story_fbid={latest_id}&id={FB_PAGE_ID}"
                log(f"✅ Найден пост: {post_url}")
                return latest_id, post_url

        log("⚠️  Посты не найдены в HTML")
        log(f"📄 HTML preview: {html[:300]}")
        return None, None

    except Exception as e:
        log(f"❌ Ошибка: {e}")
        return None, None

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
        log(f"📤 Отправляю заказ: service={JAP_SERVICE}, quantity={quantity}")
        resp = requests.post(JAP_API_URL, data=payload, timeout=15)
        log(f"📥 Ответ JAP: {resp.status_code} | {repr(resp.text[:300])}")
        if not resp.text.strip():
            log("❌ Пустой ответ от JAP")
            return
        data = resp.json()
        if "order" in data:
            log(f"✅ Заказ создан! ID: {data['order']} | Кол-во: {quantity} | {post_url}")
        elif "error" in data:
            log(f"❌ Ошибка JAP: {data['error']}")
        else:
            log(f"⚠️  Неизвестный ответ: {data}")
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
    log("🚀 Бот запущен!")
    log(f"📘 Facebook страница: {FB_PAGE_ID} | Услуга: {JAP_SERVICE} | Кол-во: {QUANTITY_MIN}–{QUANTITY_MAX}")
    check_balance()

    last_id = load_last_post_id()

    if not last_id:
        latest_id, _ = get_latest_post()
        if latest_id:
            save_last_post_id(latest_id)
            last_id = latest_id
            log(f"📌 Первый запуск. Последний пост: #{latest_id}. Жду новые...")

    while True:
        try:
            latest_id, post_url = get_latest_post()
            if latest_id and latest_id != last_id:
                log(f"🆕 Новый пост: {post_url}")
                create_jap_order(post_url)
                save_last_post_id(latest_id)
                last_id = latest_id
            else:
                log(f"🔍 Нет новых постов (последний: #{last_id})")
        except Exception as e:
            log(f"❌ Ошибка: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
