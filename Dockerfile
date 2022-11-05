FROM ubuntu:focal-20221019

# Ensure apt won't prompt for selecting options
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -yqq wget && \
    wget https://images.getsmarter.io/opencv/opencv4_4.4.0-1_python3.8_$(dpkg --print-architecture).deb && \
    apt install -yqq --no-install-recommends \
    curl \
    python3-pip \
    python3-dev \
    build-essential \
    pkg-config \
    python3-numpy \
    python3-grpcio \
    libhdf5-dev \
    ./opencv4_4.4.0-1_python3.8_$(dpkg --print-architecture).deb \
    python3-flask \
    libffi-dev \
    libssl-dev \
    python3-paho-mqtt && \
    rm opencv4_4.4.0-1_python3.8_*.deb && \
    rm -rf /var/lib/apt/lists/* && \
    wget https://images.getsmarter.io/ml-models/image-detector-models.tar.gz && \
    tar -xvzf image-detector-models.tar.gz && \
    rm image-detector-models.tar.gz

RUN python3 -m pip install --upgrade \
    wheel \
    setuptools && \
    python3 -m pip install --upgrade \
    tritonclient[all] \
    requests

COPY *.py *.classes ./
COPY templates /templates

CMD [ "bash" ]
