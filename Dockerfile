# Stage 1: Build mahjong-cpp nanikiru binary
FROM debian:12.9-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake g++ make git ca-certificates \
    libboost-dev libboost-filesystem-dev libboost-system-dev \
    && rm -rf /var/lib/apt/lists/*

COPY mahjong-cpp /build/mahjong-cpp
WORKDIR /build/mahjong-cpp

RUN mkdir -p build && cd build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SAMPLES=OFF -DBUILD_TEST=OFF \
    && make -j$(nproc) nanikiru \
    && cmake --install . --prefix install

# Stage 2: Runtime
FROM python:3.12.8-slim-bookworm

# Install nanikiru binary + data files
COPY --from=builder /build/mahjong-cpp/build/install/bin/ /opt/nanikiru/

# Python app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py mj_categorize.py mj_defense.py mj_games.py mj_parse.py ./
COPY static/ static/
COPY riichi-mahjong-tiles/Regular/ riichi-mahjong-tiles/Regular/

# Create non-root user with a home dir (gunicorn needs it) and data directories
RUN useradd -r -u 1000 -m -s /bin/false appuser \
    && mkdir -p mortal_analysis data \
    && chown -R appuser:appuser /app \
    && chmod -R o+rx /opt/nanikiru

# Environment
ENV NANIKIRU_BIN=/opt/nanikiru/nanikiru
ENV DB_PATH=/app/data/games.db
ENV PYTHONUNBUFFERED=1

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
