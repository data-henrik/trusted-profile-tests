########
# Python dependencies builder
#
# Full official Debian-based Python image
FROM python:3.8 AS builder

# Always set a working directory
WORKDIR /app
# Sets utf-8 encoding for Python et al
ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Ensures that the python and pip executables used
# in the image will be those from our virtualenv.
ENV PATH="/venv/bin:$PATH"

# Install OS package dependencies.
# Do all of this in one RUN to limit final image size.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential && \
        rm -rf /var/lib/apt/lists/*

# Setup the virtualenv
RUN python -m venv /venv

# Install Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Actual container
#
#
FROM python:3.8-slim AS app

# Extra python env
ENV PATH="/venv/bin:$PATH"

WORKDIR /app
EXPOSE 8080

# copy in Python environment
COPY --from=builder /venv /venv

RUN apt-get update && \
    apt-get install curl -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# copy in the rest of the app
COPY ./ ./
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8080","app:app"]
