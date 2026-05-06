# AmneziaWG Telegram Bot

Телеграм-бот для пошаговой генерации конфигов AmneziaWG. По команде `/config` бот собирает параметры, вызывает HTTP API генератора и отправляет готовый `.conf` файлом.

## Что умеет

- Выбор режима `legacy` или `awg2`.
- Задание шаблона, DNS-пресета, route-пресетов и override для endpoint.
- Передача `persistentKeepalive`, `i1Ref` и сырого `i1`.
- Отправка результата как документа Telegram.

## Запуск

1. Создайте виртуальное окружение.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Заполните переменные окружения:

```bash
copy .env.example .env
```

4. Укажите токен бота и при необходимости свой URL генератора:

- `TELEGRAM_BOT_TOKEN`
- `GENERATOR_API_BASE_URL`

5. Запустите бота:

```bash
python -m app.main
```

Локальная генерация конфигов

По умолчанию бот использует внешний генератор (`GENERATOR_API_BASE_URL`). Чтобы использовать встроенный локальный генератор (без внешнего API), добавьте в `.env`:

```
USE_REMOTE_GENERATOR=false
```

Локальный генератор создаёт WireGuard/Amnezia-совместимый конфиг и отправляет его как файл.`

Работа с удалённым сервером Amnezia (через SSH)

Если у вас есть развернутый сервер Amnezia в Docker и вы хотите, чтобы бот автоматически создавал клиентов на сервере и выдавал готовые конфиги, задайте в `.env` параметры SSH и WireGuard:

```
SSH_HOST=151.243.176.102
SSH_USER=root
SSH_PORT=22
SSH_KEY_PATH=/root/.ssh/id_rsa    # или SSH_PASSWORD

WIREGUARD_DOCKER_CONTAINER=amnezia-awg
WIREGUARD_INTERFACE_NAME=wg0
WIREGUARD_ENDPOINT_HOST=151.243.176.102
WIREGUARD_ENDPOINT_PORT=48360
WIREGUARD_CLIENT_NETWORK_PREFIX=10.8.1
WIREGUARD_CLIENT_START_OCTET=16
WIREGUARD_ALLOWED_IPS=0.0.0.0/0
WIREGUARD_DNS=1.1.1.1,8.8.8.8
WIREGUARD_MTU=1280
```

После этого пользователь в Telegram может отправить команду `/amnezia_quick` — бот подключится к серверу по SSH, сгенерирует ключи клиента, добавит пир в WireGuard на сервере и вернёт готовый `.conf` файл.

Внимание: бот использует `wg set` внутри контейнера для добавления пиров; убедитесь, что контейнер `amnezia-awg` имеет установленный `wireguard-tools` и что команда `wg` доступна внутри контейнера.

## Команды

- `/start` — краткая справка.
- `/config` — пошаговая генерация конфига.
- `/cancel` — отмена текущего диалога.

## Примечание

По умолчанию бот использует публичный генератор на `https://valokda-amnezia.vercel.app`. Если у вас свой деплой `amnezia-config-gen`, просто укажите его в `GENERATOR_API_BASE_URL`.

## Безопасность и загрузка на GitHub

- Никогда не коммитьте файл с реальным токеном бота. Используйте `.env` в локальной среде и добавляйте его в `.gitignore` (уже добавлен).
- Скопируйте пример и заполните токен локально:

```bash
copy .env.example .env
rem # затем отредактируйте .env и поставьте TELEGRAM_BOT_TOKEN
```

- Чтобы запушить репозиторий на GitHub, добавьте удалённый репозиторий и запушьте ветку `main` (замените URL на ваш):

```bash
git remote add origin https://github.com/<your-username>/<your-repo>.git
git branch -M main
git add -A
git commit -m "Prepare repo: add .gitignore and docs"
git push -u origin main
```

- Если вы хотите хранить токен в GitHub Actions или другом CI, используйте `Secrets` и не включайте токен в код или публичные файлы.
