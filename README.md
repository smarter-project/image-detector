<!--
waggle_topic=/plugins_and_code
-->

# Simple Car|Pedestrian Detector 

This is only a hack.

This detector mimicks behavior of the Waggle
[image detector plugin](https://github.com/waggle-sensor/plugin_manager/tree/master/plugins/image-detector.plugin),
but without requiring full pywaggle environment.

SSD mobilenet is used as backbone network and
the [COCO dataset](http://cocodataset.org/#home)
was used when trained.  The pre-trained graph can
be obtained from the
[OpenCV wiki](https://github.com/opencv/opencv/wiki/TensorFlow-Object-Detection-API).


## Getting Started

1. Install the necessary python packages.

    ```
    pip install -r requirements.txt
    ```

2. Use car_person.py to detect people or cars in a static image.

    ```
    ./car_person.py test.png
    2019-06-12 16:30:05.573273,0,0,image,car_count,1
    2019-06-12 16:30:05.573373,0,0,image,person_count,4
    ```

3. Use demo.py to continuously detect people or cars from camera feed.

    ```
    ./demo.py -h
    usage: demo.py [-h] [-d DEVNO] [-c CONFIDENCE] [-r ROTATE] [-s SLEEP]

    ./demo.py -d 1 -s 5
    2019-06-12 16:33:25.728153,0,0,image,car_count,0
    2019-06-12 16:33:25.728254,0,0,image,person_count,1
    2019-06-12 16:33:30.799255,0,0,image,car_count,0
    2019-06-12 16:33:30.799308,0,0,image,person_count,1
    ...
    ```

## Deploy to Raspberry Pi using Docker

These instructions assume that the Raspberry Pi is running a 32-bit OS image
that supports Docker. It also assumes that you have a more powerful "builder"
machine available to build the Docker image.

1. On the builder machine (not the RPi), execute the image builder script:

    ```
    ./build_image.sh
    ```

    This script should take a few minutes to run the first time - runtime will
    depend on your internet bandwidth and available system resources. When
    complete, you can type `docker images image-detector-simple` to see the
    built image. The image will be tagged with a timestamp in the form
    `YYYYMMDD_HHMMSS`, and should be less than 1GB in size - if it is more than
    that, we need to do some refactoring (the RPi won't have enough RAM to load
    the image).

2. Save the image to your filesystem as a tar file (substitute the timestamp
   with your own):

    ```
    docker save image-detector-simple:YYYYMMDD_HHMMSS -o image-detector-simple.tar
    ```

3. Transfer the image file to the RPi (assumes you have SSH access to the RPi):

    ```
    rsync -av --progress image-detector-simple.tar pi@raspberrypi.local:
    ```

    Note that `raspberrypi.local` happens to be the hostname of our RPi, but
    your own may differ. Also, please note the colon `:` at the end.

4. Now login to the RPi and load the image into the RPi's Docker:

    ```
    ssh pi@raspberrypi.local
    % docker load -i image-detector-simple.tar
    ```

    This will take a few (~2-5) minutes. When complete, you can type `docker
    images image-detector-simple` to see the loaded image.

5. While still logged into the RPi, create/run a Docker container:

    ```
    % docker network create --driver bridge test-local
    % docker run -d --rm --name fluentbit-mqtt --network test-local fluentbit-arm32v7:<YYYYMMDDHHMMSS>
    % docker run -d --rm --name image-det --network test-local image-detector-simple-arm32v7:<YYYYMMDDHHMMSS>
    ```

    The first command creates a network in docker, the second runs fluentbit (MQTT server), the third runs the image detector in a demo mode (reading the image from the test.png)

    % docker run image-detector-simple:YYYYMMDD_HHMMSS

6. (Optional) To interface with the RPi camera module, ensure that the module is
   installed properly and enabled on the RPi, then:

    ```
    % docker run -d --device=/dev/video0 --name image-det --network test-local image-detector-simple-arm32v7:<YYYYMMDDHHMMSS> python3 demo.py
    ```

    This version run the image using the RPi camera as the input. Fluentbit will output in the stdout the results.
