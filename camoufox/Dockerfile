FROM debian:bookworm-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN sed -i 's|deb.debian.org/debian|mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|deb.debian.org/debian-security|mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update && \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 install -y --no-install-recommends \
    python3 python3-pip ca-certificates curl xvfb && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple "camoufox[geoip]" playwright --break-system-packages && \
    playwright install-deps && \
    playwright install firefox && \
    python3 -m camoufox fetch

COPY launch_official_server.py /app/launch_official_server.py

ENV CAMOU_HEADLESS=true \
    CAMOU_PORT=9222 \
    CAMOU_WS_PATH=camoufox

EXPOSE 9222

CMD ["python3", "/app/launch_official_server.py"]
