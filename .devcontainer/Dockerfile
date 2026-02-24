FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# Install system dependencies required by Arches
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        libgdal-dev \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        gettext \
        build-essential \
        gdal-bin \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js 22.x
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set GDAL env vars for Python bindings
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
