FROM debian:bullseye-20191118-slim

# TODO (grebre01): reduce size of container by adding:
#    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
#    rm -rf /var/lib/apt/lists/*
# TODO (grebre01): look into upgrading pip with "pip3 install --upgrade pip"
# TODO (grebre01): look into reducing image size with "arm32v7/alpine:3.9" base image
# TODO (grebre01): check if pip package "opencv-contrib-python-headless" is somehow better

RUN apt-get update && \
    apt-get install -yqq --no-install-recommends ca-certificates \
    libhdf5-dev python3-dev python3-opencv python3-paho-mqtt python3-numpy && \
    rm -rf /var/lib/apt/lists/*

COPY *.py test.png ./
COPY models/ssd_mobilenet_coco.* ./models/

CMD [ "python3", "./car_person.py", "test.png" ]
