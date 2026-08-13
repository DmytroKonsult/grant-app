#!/usr/bin/env python3
"""
Бот для Mini App «Калькулятор гранту».

Робить одну річ: коли клієнт у чаті тисне в апці «Надіслати в розмову»,
Telegram надсилає боту inline-запит із кодом розрахунку (наприклад G-G-2100-y-5).
Бот розшифровує код і повертає готове повідомлення, яке клієнт надсилає
у вашу розмову від свого імені.

Залежностей немає — тільки стандартна бібліотека Python 3.
Потрібен лише токен бота у змінній середовища BOT_TOKEN.

Запуск для перевірки:
    BOT_TOKEN=123:ABC python3 calcbot.py
"""

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
OWNER_ID = os.environ.get("OWNER_ID", "").strip()
API = "https://api.telegram.org/bot{}/{}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("calcbot")

# Порядок мусить точно збігатися з масивом BONUSES у index.html
BONUSES = [
    ("Вік 18–25 років", 5),
    ("Ветеранське підприємництво", 20),
    ("Платник ПДВ", 20),
    ("Чинний патент", 20),
    ("ВПО або релокований бізнес", 20),
    ("2+ робочих місць", 20),
    ("Прифронтовий регіон", 30),
    ("Оновлення знищених засобів", 30),
    ("Пріоритетний сектор", 50),
]

TYPES = {"S": "Відкриття справи", "G": "Масштабування власної справи"}


def money(n):
    return "{:,}".format(int(n)).replace(",", " ") + " ₴"


def years_word(t):
    return "років" if t == 5 else "роки"


def decode(payload):
    """G-G-2100-y-5 -> dict або None."""
    parts = payload.split("-")
    if len(parts) != 5 or parts[0] != "G" or parts[1] not in TYPES:
        return None
    try:
        total = int(parts[2]) * 1000
        mask = int(parts[3], 36)
        years = int(parts[4])
    except ValueError:
        return None
    if years not in (2, 3, 5) or total <= 0:
        return None

    picked = [(n, p) for i, (n, p) in enumerate(BONUSES) if mask >> i & 1]
    return {
        "type": TYPES[parts[1]],
        "sum": total,
        "bonus_pct": sum(p for _, p in picked),
        "bonuses": [n for n, _ in picked],
        "term": years,
        "monthly": round(total / (years * 12)),
        "fee": round(total * 0.05) + 5000,
    }


def build_message(d):
    """Текст, який клієнт надішле у вашу розмову."""
    bonuses = ", ".join(d["bonuses"]) if d["bonuses"] else "немає"
    return (
        "📄 Мій розрахунок гранту\n\n"
        "Напрям: {}\n"
        "Максимум: {}\n"
        "Бонуси: +{}% ({})\n"
        "Строк: {} {}\n"
        "Податків: {}/міс\n"
        "Супровід: {}"
    ).format(
        d["type"], money(d["sum"]), d["bonus_pct"], bonuses,
        d["term"], years_word(d["term"]), money(d["monthly"]), money(d["fee"]),
    )


def api(method, payload, timeout=65):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API.format(TOKEN, method),
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        log.error("%s -> HTTP %s: %s", method, e.code, body)
        if e.code == 409:
            log.error("КОНФЛІКТ: цей токен уже слухає інший процес або вебхук. "
                      "Дивись розділ 'Помилка 409' в інструкції.")
        return None
    except Exception as e:
        log.error("%s -> %s", method, e)
        return None


def answer_inline(query_id, d):
    if d is None:
        api("answerInlineQuery", {
            "inline_query_id": query_id,
            "results": [],
            "cache_time": 0,
            "is_personal": True,
            "button": {"text": "Відкрити калькулятор",
                       "start_parameter": "calc"},
        })
        return

    api("answerInlineQuery", {
        "inline_query_id": query_id,
        "cache_time": 0,
        "is_personal": True,
        "results": [{
            "type": "article",
            "id": "calc",
            "title": "Надіслати: " + money(d["sum"]),
            "description": "{} · {} {}".format(
                d["type"], d["term"], years_word(d["term"])),
            "input_message_content": {"message_text": build_message(d)},
        }],
    })


def handle_start(msg):
    """Резервний шлях: /start G-G-2100-y-5"""
    text = (msg.get("text") or "").strip()
    if not text.startswith("/start"):
        return
    parts = text.split(None, 1)
    payload = parts[1].strip() if len(parts) > 1 else ""
    chat_id = msg["chat"]["id"]

    if not payload.startswith("G-"):
        api("sendMessage", {
            "chat_id": chat_id,
            "text": "Вітаю! Відкрийте калькулятор кнопкою в меню, "
                    "щоб порахувати свій максимум за програмою гранту.",
        })
        return

    d = decode(payload)
    if not d:
        return

    api("sendMessage", {"chat_id": chat_id, "text": build_message(d)})

    if OWNER_ID:
        u = msg.get("from", {})
        who = "@" + u["username"] if u.get("username") else "без username"
        name = " ".join(filter(None, [u.get("first_name"), u.get("last_name")]))
        api("sendMessage", {
            "chat_id": OWNER_ID,
            "text": "🟢 НОВИЙ ЛІД\n\n{}\n\nКлієнт: {} · {}\nID: {}".format(
                build_message(d), name or "без імені", who, u.get("id")),
        })


def main():
    if not TOKEN:
        log.error("BOT_TOKEN не заданий. Запусти так: BOT_TOKEN=токен python3 calcbot.py")
        sys.exit(1)

    me = api("getMe", {}, timeout=20)
    if not me or not me.get("ok"):
        log.error("Токен не працює — перевір значення BOT_TOKEN")
        sys.exit(1)
    log.info("Запущено як @%s", me["result"].get("username"))

    offset = 0
    while True:
        upd = api("getUpdates", {
            "offset": offset,
            "timeout": 50,
            "allowed_updates": ["inline_query", "message"],
        })

        if not upd or not upd.get("ok"):
            time.sleep(5)
            continue

        for u in upd["result"]:
            offset = u["update_id"] + 1
            try:
                if "inline_query" in u:
                    q = u["inline_query"]
                    query = (q.get("query") or "").strip()
                    log.info("inline: %s", query or "(порожній)")
                    answer_inline(q["id"], decode(query) if query else None)
                elif "message" in u:
                    handle_start(u["message"])
            except Exception:
                log.exception("Помилка обробки update %s", u.get("update_id"))


if __name__ == "__main__":
    main()
