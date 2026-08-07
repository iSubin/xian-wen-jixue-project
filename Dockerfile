FROM node:20-alpine AS frontend-build

WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm ci --no-audit --fund=false

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/xianwen

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        git \
        libgomp1 \
        openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system xianwen \
    && useradd --system --create-home --gid xianwen --shell /usr/sbin/nologin xianwen

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=xianwen:xianwen xianwen-app.py ./
COPY --chown=xianwen:xianwen src ./src
COPY --chown=xianwen:xianwen config/settings.example.json ./config/settings.example.json
COPY --from=frontend-build --chown=xianwen:xianwen /build/frontend/dist ./frontend/dist

RUN mkdir -p /app/config /app/temp /home/xianwen/.cache \
    && chown -R xianwen:xianwen /app/config /app/temp /home/xianwen

USER xianwen

EXPOSE 8000

CMD ["python", "xianwen-app.py"]
