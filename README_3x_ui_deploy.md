# Развёртывание 3x-ui и FastAPI backend (prod-ready рекомендации)

Ниже — пошаговая инструкция по развёртыванию `3x-ui` как отдельного фронтенд-сервиса и `backend` (FastAPI) для управления Amnezia.

1) Подготовка сервера
  - OS: Debian/Ubuntu 22.04+ или аналог.
  - Установите Docker и docker-compose.

2) Клонирование репозитория и конфигурация
  - Клонируйте этот репозиторий в `~/vpn-2` или используйте уже существующую папку, где у тебя лежит код.
  - Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

    TELEGRAM_BOT_TOKEN=...
    SSH_HOST=your.amnezia.host
    SSH_USER=root
    SSH_KEY_PATH=/root/.ssh/id_rsa
    WIREGUARD_DOCKER_CONTAINER=amnezia-awg
    WIREGUARD_INTERFACE_NAME=wg0
    WIREGUARD_ENDPOINT_HOST=example.com
    WIREGUARD_ENDPOINT_PORT=51820

3) Запуск backend
  - Быстрый запуск (локально):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

  - Для продакшна рекомендую использовать Postgres (заменить `DATABASE_URL`) и запустить через systemd + docker-compose или k8s.

4) Развёртывание 3x-ui (frontend)
  - Получите исходники 3x-ui (репозиторий 3x-ui). Если это статический SPA, соберите проект:

```bash
git clone <3x-ui-repo>
cd 3x-ui
# пример для npm-based
npm ci
npm run build
# результат в dist/ или build/
```

  - Вариант A: разместить как статические файлы через nginx
    - Подготовьте nginx-конфигурацию, которая проксирует API-запросы `/api` на `http://backend:8000` и отдаёт статические файлы.

  - Вариант B: собрать Docker-образ фронтенда и запустить через docker-compose, пример nginx-proxy в одном стеке.

5) HTTPS и домен
  - Используйте nginx + certbot для получения TLS сертификата.
  - Настройте nginx site с proxy_pass на backend и корневую отдачу статичных файлов 3x-ui.

6) Auth / Billing
  - Для продакшна обязательно добавить аутентификацию (OAuth2/JWT) на backend и защиту админ API.
  - Интеграция биллинга зависит от провайдера (Stripe/CloudPayments): создайте микросервис оплаты и привяжите к пользователю / peer.

7) Дополнительно: персистентность peer'ов
  - Backend должен сохранять peers в БД и при перезапуске контейнера Amnezia восстанавливать записи в `wg0.conf` (через SSH и безопасное редактирование файла + перезагрузка сервиса внутри контейнера).

  9) Production: docker-compose, systemd и TLS

    - Пример `docker-compose.prod.yml` добавлен в репозитории. Скопируйте его на сервер в `/srv/amnezia/docker-compose.prod.yml` и создайте файл с секретами (`.env`) с переменными: `POSTGRES_PASSWORD`, `JWT_SECRET`, `ADMIN_USER`, `ADMIN_PASS`, `SSH_KEY_PATH` и т.д.

    - Пример systemd unit: `systemd/amnezia-backend.service` — сохраняется как `/etc/systemd/system/amnezia-backend.service`. После размещения файлов выполните:

  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable --now amnezia-backend.service
  ```

    - Настройка TLS (Certbot + nginx): убедитесь, что `nginx` в `docker-compose.prod.yml` отдаёт фронтенд и проксирует `/api` на backend. На хосте установите `certbot` и запустите:

  ```bash
  sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
  # настройте nginx конфигурацию (см. nginx.prod.conf)
  sudo certbot --nginx -d example.com
  ```

    - Рекомендация по секретам: храните `POSTGRES_PASSWORD` и `JWT_SECRET` в секретном хранилище (Vault / GitHub Secrets / Environment) и не коммитьте их в репозиторий.

8) Примеры команд

```bash
# запустить backend
docker-compose up -d --build backend

# обновить nginx и получить TLS
sudo apt install nginx certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

Если хочешь, я могу: сгенерировать пример `nginx`-конфигурации и docker-compose стек, подготовить миграции для Postgres и добавить аутентификацию (JWT) — скажи, какие шаги приоритетнее.
