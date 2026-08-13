"""
Inline-обробник Mini App «Калькулятор гранту».

Клієнт в апці тисне «Надіслати в розмову» — Telegram надсилає боту
inline-запит із кодом розрахунку (наприклад G-G-2100-y-5). Бот повертає
готове повідомлення, яке клієнт надсилає у вашу розмову від свого імені.

Підключення (файл telegram_bot.py, функція main):

    from calc_inline import register_calc

    app = Application.builder().token(TOKEN).build()
    register_calc(app)          # <- цей рядок
    app.add_handler(CommandHandler('start', start))
    ...

Нічого наявного не змінює: реагує лише на inline-запити.
"""

import logging
from uuid import uuid4

from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import ContextTypes, InlineQueryHandler

log = logging.getLogger(__name__)

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


def _money(n: int) -> str:
    return f"{int(n):,}".replace(",", " ") + " ₴"


def _years(t: int) -> str:
    return "років" if t == 5 else "роки"


def decode(payload: str):
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
    if years not in (2, 3, 5) or not 0 < total <= 10_000_000:
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


def build_message(d: dict) -> str:
    """Текст, який з'явиться у вашій розмові від імені клієнта."""
    bonuses = ", ".join(d["bonuses"]) if d["bonuses"] else "немає"
    return (
        "📄 Мій розрахунок гранту\n\n"
        f"Напрям: {d['type']}\n"
        f"Максимум: {_money(d['sum'])}\n"
        f"Бонуси: +{d['bonus_pct']}% ({bonuses})\n"
        f"Строк: {d['term']} {_years(d['term'])}\n"
        f"Податків: {_money(d['monthly'])}/міс\n"
        f"Супровід: {_money(d['fee'])}"
    )


async def inline_calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = (update.inline_query.query or "").strip()

    if not query.startswith("G-"):
        await update.inline_query.answer([], cache_time=0, is_personal=True)
        return

    data = decode(query)
    if data is None:
        log.warning("Калькулятор: не розпізнано payload %r", query)
        await update.inline_query.answer([], cache_time=0, is_personal=True)
        return

    log.info("Калькулятор: inline %s -> %s", query, data["sum"])

    result = InlineQueryResultArticle(
        id=str(uuid4()),
        title=f"Надіслати: {_money(data['sum'])}",
        description=f"{data['type']} · {data['term']} {_years(data['term'])}",
        input_message_content=InputTextMessageContent(build_message(data)),
    )
    await update.inline_query.answer([result], cache_time=0, is_personal=True)


def register_calc(app) -> None:
    """Викликати в main() після створення Application."""
    app.add_handler(InlineQueryHandler(inline_calc))
    log.info("Калькулятор: inline-обробник зареєстровано")
