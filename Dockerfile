FROM python:3.12-slim

WORKDIR /app

# SSH 클라이언트 설치 및 ubuntu 사용자 생성 (oci2 서버 메트릭 수집용)
# docker-compose에서 user: "1001:1001"로 실행하므로 uid 1001에 맞춰 생성
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -u 1001 -m -d /home/ubuntu -s /bin/bash ubuntu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/tmp/uv-cache \
    HOME=/home/ubuntu \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

COPY . .

CMD ["/opt/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
