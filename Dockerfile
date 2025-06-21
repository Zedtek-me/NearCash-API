FROM python:3.13

WORKDIR /app
COPY . /app/
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libspatialindex-dev \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* &&\
    pip install --no-cache-dir -r requirements.txt 
RUN chmod +x ./start_local.sh
ENTRYPOINT ["sh", "start_local.sh"]
