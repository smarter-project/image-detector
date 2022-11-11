<!--
waggle_topic=/plugins_and_code
-->

# Simple Car|Pedestrian Detector 

This is only a hack.

This detector mimicks the original behavior of the Waggle
[image detector plugin](https://github.com/waggle-sensor/plugin_manager/tree/master/plugins/image-detector.plugin),
but without requiring full pywaggle environment.

SSD mobilenet is used as backbone network and
the [COCO dataset](http://cocodataset.org/#home)
was used when trained.  The pre-trained graph can
be obtained from the
[OpenCV wiki](https://github.com/opencv/opencv/wiki/TensorFlow-Object-Detection-API).

This detector relies on Nvidia Triton inference server to perform the actual car/pedestrian counting. The application uses opencv to read images from an image source, generates a tensor for the image, and sends it via gRPC or HTTP to triton where the actual inference is performed. If an instance of triton is not running or accessible on the node (with model `ssd_mobilenet_coco` available) this application is run, it will fail and restart

For demonstration/debugging purposes, the app can be configured to expose a flask web application which displays the most recent image with annotations for the detected people and cars.

## Arguments
The following arguments are available to configure the image detector:
- `-f,--flask` - if set flask app will run at `LISTEN_IP:LISTEN_PORT`
- `-v,--verbose` - enable verbose output
- `-i,--ip` or env var `LISTEN_IP` - listen IP address for web server if enabled. Default is `0.0.0.0`
- `--port` or env var `LISTEN_PORT` - listen port for web server if enabled
- `-d,--devno` or env var `DEVNO` - device number for camera (default -1=find first available, 0=internal, 1=external), only used if `CAPTURE_STRING` not set
- `-n,--capture-string` or env var `CAPTURE_STRING` - any valid VideoCapture string(IP camera connection, RTSP connection string
- `-c,--confidence` or env var `CONFIDENCE` - minimum confidence score for a detection to register, default is 0.3
- `-p,--publish` - if flag or env var set, results of detection will be published to `MQTT_BROKER_HOST`:1883, default is "fluent-bit"
- `-s,--sleep` or env var `SLEEP` - after each detection, sleep for a set number of seconds, default is 1.0
- `--protocol` or env var `PROTOCOL` - protocol to send requests to triton inference server, default is HTTP, other option is gRPC
- `-m,--model-name` or env var `MODEL_NAME` - model name in triton to perform inference against, default is `ssd_mobilenet_coco`
- `-x,--model-version` or env var `MODEL_VERSION` - Version of model to use in triton, default is latest version
- `-u,--triton-url` or env var `TRITON_URL` - url to access triton, default is localhost:8000
- `--smarter-inference-url` or env var `SMARTER_INFERENCE_URL` - url to access smarter-inference, default is empty string. If set, triton url will be overwritten within smarter-inference inference access point
- `-b,--mqtt-broker-host` or env var `MQTT_BROKER_HOST` - host to access mqtt broker, default to `fluent-bit`
- `--mqtt-broker-port` or env var `MQTT_BROKER_PORT` - port to access mqtt broker, default to 1883
- `-t,--mqtt-topic` or env var `MQTT_TOPIC` - mqtt topic to post messages under, default to `/demo`
- `--db1,--detect-car`- if set will detect cars
- `--db2,--detect-person` - if set will detect people
- `--db3,--detect-bus` - if set will detect buses
- `--db4,--detect-bicycle` - if set will detect bicycles
- `--db5,--detect-motorcycle`- if set will detect motorcycles




