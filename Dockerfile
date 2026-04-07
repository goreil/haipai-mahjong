# Stage 1: Build mahjong-cpp shared library
FROM debian:12.9-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake g++ make git ca-certificates \
    libboost-dev libboost-filesystem-dev libboost-system-dev \
    && rm -rf /var/lib/apt/lists/*

COPY mahjong-cpp /build/mahjong-cpp
WORKDIR /build/mahjong-cpp

RUN mkdir -p build && cd build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_PYTHON=ON -DBUILD_SERVER=OFF -DBUILD_SAMPLES=OFF -DBUILD_TEST=OFF \
    && make -j$(nproc) mahjong-python \
    && cmake --install . --prefix install

# Stage 2: Runtime
FROM python:3.12.8-slim-bookworm

# Install shared library + data files (libmahjongcpp.so + .bin/.json lookup tables)
COPY --from=builder /build/mahjong-cpp/build/install/lib/ /opt/mahjong-cpp/
# Copy Boost shared libs needed at runtime (version-agnostic)
COPY --from=builder /usr/lib/*/libboost_filesystem.so* /usr/lib/
COPY --from=builder /usr/lib/*/libboost_system.so* /usr/lib/

# Python app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py routes_games.py routes_practice.py routes_admin.py db.py mahjong_cpp.py mj_categorize.py mj_defense.py mj_games.py mj_parse.py ./
COPY static/ static/
COPY riichi-mahjong-tiles/Regular/ riichi-mahjong-tiles/Regular/

# Create non-root user with a home dir (gunicorn needs it) and data directories
RUN useradd -r -u 1000 -m -s /bin/false appuser \
    && mkdir -p mortal_analysis data \
    && chown -R appuser:appuser /app \
    && chmod -R o+rx /opt/mahjong-cpp

# Environment
ENV MAHJONG_CPP_LIB=/opt/mahjong-cpp/libmahjongcpp.so
ENV DB_PATH=/app/data/games.db
ENV PYTHONUNBUFFERED=1

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
