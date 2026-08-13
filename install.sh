#!/usr/bin/env bash
#
# Інсталятор бота калькулятора грантів.
#
# Запуск на сервері однією командою:
#
#   curl -sL https://raw.githubusercontent.com/DmytroKonsult/grant-app/main/install.sh -o /tmp/i.sh && BOT_TOKEN='ТОКЕН' OWNER_ID='ID' bash /tmp/i.sh
#
# Що робить:
#   1. перевіряє Python і токен
#   2. звільняє токен від вебхука, якщо той стоїть
#   3. качає calcbot.py з репозиторію
#   4. створює службу systemd з автозапуском
#   5. запускає і показує результат

set -euo pipefail

REPO="https://raw.githubusercontent.com/DmytroKonsult/grant-app/main"
DIR="/opt/calcbot"
UNIT="/etc/systemd/system/calcbot.service"

green() { printf "\033[0;32m%s\033[0m\n" "$1"; }
red()   { printf "\033[0;31m%s\033[0m\n" "$1"; }
step()  { printf "\n\033[1m%s\033[0m\n" "$1"; }

# --- Перевірка вхідних даних ---------------------------------------------
if [ -z "${BOT_TOKEN:-}" ]; then
  red "Не заданий BOT_TOKEN."
  echo "Запускай так:"
  echo "  BOT_TOKEN='токен' OWNER_ID='твій_id' bash /tmp/i.sh"
  exit 1
fi

OWNER_ID="${OWNER_ID:-}"

# --- 1. Python ------------------------------------------------------------
step "1/6  Перевіряю Python"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python не знайдено, встановлюю..."
  apt-get update -qq && apt-get install -y -qq python3
fi
green "OK  $(python3 --version)"

# --- 2. Токен -------------------------------------------------------------
step "2/6  Перевіряю токен"
ME=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
if ! echo "$ME" | grep -q '"ok":true'; then
  red "Токен не працює. Перевір, чи скопійований повністю."
  echo "$ME"
  exit 1
fi
USERNAME=$(echo "$ME" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
green "OK  бот @${USERNAME}"

# --- 3. Вебхук ------------------------------------------------------------
step "3/6  Перевіряю, чи вільний токен"
WH=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
WH_URL=$(echo "$WH" | sed -n 's/.*"url":"\([^"]*\)".*/\1/p')
if [ -n "$WH_URL" ]; then
  echo "Знайдено вебхук: $WH_URL"
  echo "Знімаю його, бо інакше бот не отримуватиме запити..."
  curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook" >/dev/null
  green "OK  вебхук знято"
else
  green "OK  токен вільний"
fi

# --- 4. Файл бота ---------------------------------------------------------
step "4/6  Завантажую бота"
mkdir -p "$DIR"
if ! curl -fsSL "${REPO}/calcbot.py" -o "${DIR}/calcbot.py"; then
  red "Не вдалося завантажити calcbot.py"
  echo "Перевір, що файл лежить у репозиторії grant-app у гілці main."
  exit 1
fi
python3 -c "import ast,sys; ast.parse(open('${DIR}/calcbot.py').read())" || {
  red "Файл побитий"; exit 1; }
green "OK  $(wc -l < "${DIR}/calcbot.py") рядків, синтаксис цілий"

# --- 5. Служба ------------------------------------------------------------
step "5/6  Налаштовую автозапуск"
systemctl stop calcbot 2>/dev/null || true

cat > "$UNIT" <<EOF
[Unit]
Description=Grant calculator inline bot
After=network-online.target

[Service]
Type=simple
WorkingDirectory=${DIR}
Environment="BOT_TOKEN=${BOT_TOKEN}"
Environment="OWNER_ID=${OWNER_ID}"
ExecStart=/usr/bin/python3 ${DIR}/calcbot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

chmod 600 "$UNIT"
systemctl daemon-reload
systemctl enable calcbot >/dev/null 2>&1
systemctl restart calcbot
green "OK  служба створена"

# --- 6. Перевірка ---------------------------------------------------------
step "6/6  Перевіряю запуск"
sleep 4

if systemctl is-active --quiet calcbot; then
  green "OK  бот працює"
else
  red "Бот не запустився. Останні рядки логу:"
  journalctl -u calcbot -n 20 --no-pager
  exit 1
fi

if journalctl -u calcbot -n 30 --no-pager 2>/dev/null | grep -q "409"; then
  red "УВАГА: помилка 409 — цей токен слухає ще хтось."
  echo "Створи окремого бота в BotFather під калькулятор."
fi

printf "\n\033[1;32m═══════════════════════════════════════\033[0m\n"
green " ГОТОВО"
printf "\033[1;32m═══════════════════════════════════════\033[0m\n\n"
echo "Бот:      @${USERNAME}"
echo "Папка:    ${DIR}"
if [ -z "$OWNER_ID" ]; then
  echo "OWNER_ID: не заданий (ліди в особисті не дублюються)"
else
  echo "OWNER_ID: ${OWNER_ID}"
fi

cat <<'NEXT'

ЩО ЗРОБИТИ ДАЛІ

1. У @BotFather перевір, що ввімкнений Inline Mode:
   /mybots -> бот -> Bot Settings -> Inline Mode

2. Візьми телефон, відкрий апку з будь-якого чату,
   порахуй і тисни «Надіслати в розмову».

3. Дивись живий лог тут:
   journalctl -u calcbot -f
   (вихід — Ctrl+C)

   Має з'явитись рядок:  inline: G-G-2100-y-5

КОРИСНІ КОМАНДИ

   systemctl status calcbot      стан
   systemctl restart calcbot     перезапуск
   journalctl -u calcbot -f      живий лог

ОНОВЛЕННЯ БОТА В МАЙБУТНЬОМУ

   Залий новий calcbot.py на GitHub, потім тут:
   cd /opt/calcbot && curl -O https://raw.githubusercontent.com/DmytroKonsult/grant-app/main/calcbot.py && systemctl restart calcbot

NEXT
