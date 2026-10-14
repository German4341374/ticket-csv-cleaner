# syntax=docker/dockerfile:1
FROM python:3.14.8-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.14.8-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83 AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 10001 cleaner \
    && useradd --uid 10001 --gid cleaner --create-home --shell /usr/sbin/nologin cleaner

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-index --find-links /wheels ticket-csv-cleaner==1.0.0 \
    && rm -rf /wheels

WORKDIR /work
USER 10001:10001
ENTRYPOINT ["ticket-csv-cleaner"]
CMD ["--help"]
