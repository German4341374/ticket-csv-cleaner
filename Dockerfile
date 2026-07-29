# syntax=docker/dockerfile:1
FROM python:3.14.6-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.14.6-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30 AS runtime

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
