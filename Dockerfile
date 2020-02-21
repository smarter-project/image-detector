FROM debian:bullseye-20191118-slim

RUN apt-get update && \
    apt-get install -yqq --no-install-recommends ca-certificates \
    libhdf5-dev python3-dev python3-opencv python3-paho-mqtt python3-numpy && \
    rm -rf /var/lib/apt/lists/*

COPY *.py test.png ./
COPY models/ssd_mobilenet_coco.* ./models/

CMD [ "python3", "./car_person.py", "test.png" ]
