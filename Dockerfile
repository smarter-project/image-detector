FROM debian:jessie-slim

# TODO (grebre01): reduce size of container by adding:
#    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
#    rm -rf /var/lib/apt/lists/*
# TODO (grebre01): look into upgrading pip with "pip3 install --upgrade pip"
# TODO (grebre01): look into reducing image size with "arm32v7/alpine:3.9" base image
# TODO (grebre01): check if pip package "opencv-contrib-python-headless" is somehow better

RUN apt-get update && \
    dpkg --add-architecture armhf && \
    apt-get install -yqq --no-install-recommends ca-certificates netbase curl python3-dev \
    libhdf5-dev libfreetype6-dev libharfbuzz-dev libatlas3-base libwebp5 libtiff5 libjasper1 \
    libilmbase6 libopenexr6 libgstreamer1.0-0 libavcodec56 libavformat56 libswscale3 libqtgui4 libqt4-test && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN curl -LO https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py && \
    echo "[global]\nextra-index-url=https://www.piwheels.org/simple" > /etc/pip.conf && \
    rm get-pip.py && \
    pip3 install --no-cache-dir -r requirements.txt

COPY *.py test.png ./
COPY models/ssd_mobilenet_coco.* ./models/

ENTRYPOINT [ "python3", "demo.py", "-d 1", "-s 5" ]
