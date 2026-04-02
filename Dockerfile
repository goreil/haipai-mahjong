# Stage 1: Build mahjong-cpp nanikiru binary
FROM debian:12-slim AS builder

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
FROM python:3.12-slim

# Install nanikiru binary + data files
COPY --from=builder /build/mahjong-cpp/build/install/bin/ /opt/nanikiru/

# Python app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py mj_categorize.py mj_defense.py mj_games.py mj_parse.py ./
COPY static/ static/
COPY riichi-mahjong-tiles/Regular/ riichi-mahjong-tiles/Regular/

# Create non-root user and data directories
RUN useradd -r -s /bin/false appuser \
    && mkdir -p mortal_analysis data \
    && chown -R appuser:appuser /app

# Environment
ENV NANIKIRU_BIN=/opt/nanikiru/nanikiru
ENV DB_PATH=/app/data/games.db
ENV PYTHONUNBUFFERED=1

USER appuser
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
