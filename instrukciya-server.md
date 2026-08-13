# Налаштування бота на сервері — з нуля

Читай зверху вниз, не перескакуй. Кожен блок — це команда, яку копіюєш і вставляєш у Термінал. Після кожної тисни **Enter**.

---

## Що куди йде

Щоб не заплутатись, дві різні речі в різні місця:

| Файл | Куди | Навіщо |
|---|---|---|
| `grant-miniapp.html` | на **GitHub** (як `index.html`) | сама апка, яку бачить клієнт |
| `calcbot.py` | на **сервер** | програма, що обробляє натискання кнопки |

Це два незалежних кроки. Обидва потрібні.

---

## ЧАСТИНА 1. Файл на GitHub

Спочатку простіше — те, що ти вже вмієш.

### 1.1 Залий апку
Перейменуй `grant-miniapp.html` на `index.html` → github.com/DmytroKonsult/grant-app → **Add file → Upload files** → перетягни → **Commit changes**.

### 1.2 Залий туди ж файл бота
**Add file → Upload files** → перетягни `calcbot.py` **без перейменування** → **Commit changes**.

Це потрібно, щоб потім завантажити його на сервер однією командою, а не копіювати код руками. Токена у файлі немає, тому публічність не шкодить.

### 1.3 Онови адресу в BotFather
@BotFather → `/mybots` → `@Grant_Expert_BDM_Bot` → **Mini Apps** → твій Direct Link `calc` → **Edit Web App URL**:
```
https://dmytrokonsult.github.io/grant-app/?v=20
```

---

## ЧАСТИНА 2. Сервер

### 2.1 Відкрий Термінал

На Mac: **Cmd + Space** → набери `Термінал` → Enter.

Відкриється чорне (або біле) вікно з рядком, що закінчується на `%` або `$`. Це командний рядок твого Mac.

### 2.2 Підключись до сервера

```bash
ssh root@65.108.144.129
```

Що станеться:
- якщо запитає `Are you sure you want to continue connecting?` — набери `yes` і Enter
- якщо запитає `password:` — введи пароль сервера. **Символи не відображаються, це нормально**, просто набирай і тисни Enter

Ознака успіху: рядок зміниться на щось типу `root@ubuntu:~#`. Тепер усі команди виконуються **на сервері**, а не на твоєму Mac.

### 2.3 Запиши токен у змінну

Візьми новий токен із BotFather. Замінюй `ТУТ_ТОКЕН` на нього, лапки залиш:

```bash
export T='ТУТ_ТОКЕН'
```

Нічого не виведе — так і має бути. Перевір, що записалось:

```bash
echo $T
```

Мусиш побачити свій токен.

### 2.4 Перевір, чи токен вільний

**Найважливіший крок.** Telegram дозволяє одному токену працювати лише з одним процесом. Якщо там уже щось є — бот не запуститься.

```bash
curl -s "https://api.telegram.org/bot$T/getWebhookInfo"
```

Відповідь буде схожа на `{"ok":true,"result":{"url":"","has_custom_certificate":false,...}}`

Дивись на `"url"`:
- **`"url":""`** (порожньо) → добре, йди далі
- **`"url":"https://щось..."`** → токен зайнятий вебхуком. Виконай:
  ```bash
  curl -s "https://api.telegram.org/bot$T/deleteWebhook"
  ```

Ще перевірка — чи не працює вже якась програма з ботом:

```bash
ps aux | grep -iE "python|node" | grep -v grep
```

Якщо вивід порожній — чисто. Якщо щось є, скинь мені цей текст перед продовженням.

### 2.5 Перевір, чи є Python

```bash
python3 --version
```

Мусить вивести `Python 3.x.x`. Якщо пише `command not found`:
```bash
apt update && apt install -y python3
```

### 2.6 Створи папку і завантаж файл бота

```bash
mkdir -p /opt/calcbot
cd /opt/calcbot
curl -O https://dmytrokonsult.github.io/grant-app/calcbot.py
```

Розшифровка:
- `mkdir -p /opt/calcbot` — створює папку
- `cd /opt/calcbot` — переходить у неї
- `curl -O ...` — завантажує файл з твого ж GitHub

Перевір, що файл на місці й не побитий:

```bash
ls -la calcbot.py
python3 -c "import ast; ast.parse(open('/opt/calcbot/calcbot.py').read()); print('файл цілий')"
```

Мусиш побачити розмір файла і надпис `файл цілий`.

Якщо `curl` пише 404 — значить файл ще не залитий на GitHub або деплой не добіг. Зачекай хвилину і повтори.

### 2.7 Дізнайся свій Telegram ID

У Telegram напиши боту **@userinfobot** будь-що. Він відповість числом виду `123456789`. Це твій ID — потрібен, щоб бот дублював тобі ліди особисто.

### 2.8 Перший запуск — руками

Підстав свій ID замість `ТВІЙ_ID`:

```bash
BOT_TOKEN="$T" OWNER_ID='ТВІЙ_ID' python3 calcbot.py
```

Мусиш побачити:
```
2026-08-13 13:00:00 INFO Запущено як @Grant_Expert_BDM_Bot
```

**Не закривай термінал і не тисни нічого.** Бот працює і чекає.

Тепер бери телефон:
1. Відкрий будь-який чат у Telegram (можна «Збережене»)
2. Надішли собі `t.me/Grant_Expert_BDM_Bot/calc` і тапни
3. Постав пару галочок, тисни **«Надіслати в розмову»**

У терміналі має з'явитись рядок:
```
INFO inline: G-G-2100-y-5
```

А на телефоні над клавіатурою — результат «Надіслати: 2 100 000 ₴». Тапаєш його, і розрахунок іде в чат.

**Спрацювало** → тисни **Ctrl+C** щоб зупинити, і переходь до 2.9.

**Помилка 409 Conflict** → вернись до 2.4.

**Рядок `inline:` не з'явився** → значить Telegram не надсилає запити. Перевір, що Inline Mode увімкнений у BotFather і що токен у команді — саме від `@Grant_Expert_BDM_Bot`.

### 2.9 Постійна робота

Зараз бот працює лише поки відкритий термінал. Зробимо, щоб працював завжди і сам піднімався після перезавантаження сервера.

Створюємо файл сервісу — вставляй **весь блок цілком**, разом із `EOF`:

```bash
cat > /etc/systemd/system/calcbot.service <<'EOF'
[Unit]
Description=Grant calculator inline bot
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/calcbot
Environment="BOT_TOKEN=ЗАМІНИТИ_ТОКЕН"
Environment="OWNER_ID=ЗАМІНИТИ_ID"
ExecStart=/usr/bin/python3 /opt/calcbot/calcbot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

Тепер підставимо справжні значення. Відкрий файл у редакторі:

```bash
nano /etc/systemd/system/calcbot.service
```

Як користуватись nano:
- пересувайся **стрілками** (мишка не працює)
- знайди рядок `Environment="BOT_TOKEN=ЗАМІНИТИ_ТОКЕН"`, видали `ЗАМІНИТИ_ТОКЕН` клавішею Delete і встав токен (Cmd+V)
- те саме з `ЗАМІНИТИ_ID`
- зберегти: **Ctrl+O** → Enter
- вийти: **Ctrl+X**

Запускаємо:

```bash
systemctl daemon-reload
systemctl enable --now calcbot
systemctl status calcbot --no-pager
```

Мусиш побачити зелене **active (running)**. Вихід із перегляду — клавіша `q`.

### 2.10 Фінальна перевірка

```bash
journalctl -u calcbot -n 20 --no-pager
```

Має бути рядок `Запущено як @Grant_Expert_BDM_Bot`.

Ще раз перевір з телефона — тапни кнопку в апці. Потім подивись живі логи:

```bash
journalctl -u calcbot -f
```

Вихід — **Ctrl+C**.

---

## Готово

Тепер бот працює постійно. Можеш закрити термінал — він продовжить.

---

## Шпаргалка на майбутнє

**Подивитись, чи живий:**
```bash
ssh root@65.108.144.129 "systemctl status calcbot --no-pager"
```

**Перезапустити:**
```bash
ssh root@65.108.144.129 "systemctl restart calcbot"
```

**Оновити файл бота після змін на GitHub:**
```bash
ssh root@65.108.144.129
cd /opt/calcbot && curl -O https://dmytrokonsult.github.io/grant-app/calcbot.py
systemctl restart calcbot
journalctl -u calcbot -n 20 --no-pager
```

**Логи за останню годину:**
```bash
ssh root@65.108.144.129 "journalctl -u calcbot --since '1 hour ago' --no-pager"
```

---

## Якщо щось не так

| Симптом | Причина | Дія |
|---|---|---|
| `409 Conflict` у логах | токен слухає ще хтось | пункт 2.4 |
| `inline:` не з'являється | Inline Mode вимкнений | BotFather → Bot Settings → Inline Mode |
| кнопка в апці нічого не робить | старий HTML у кеші | змінити `?v=` у BotFather |
| `curl: 404` | файл не на GitHub | залити `calcbot.py` в репо |
| `Permission denied` при ssh | невірний пароль | перевір доступ у Hetzner |
| бот замовк після перезавантаження | не зроблено `enable` | `systemctl enable calcbot` |
