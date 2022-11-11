#!/usr/bin/env python
import argparse
import logging
import os
import sys
import threading
import time
from datetime import datetime

import cv2
import paho.mqtt.client as mqtt
import requests
import tritonclient.grpc as grpcclient
import tritonclient.http as httpclient
from flask import Flask, Response, render_template
from tritonclient.utils import InferenceServerException

from classify_image import *

# Set arg parse arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    "-f", "--flask", action="store_true", help="enable flask app"
)
parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    required=False,
    default=False,
    help="Enable verbose output",
)
parser.add_argument(
    "-i",
    "--ip",
    type=str,
    required=False,
    default=os.getenv("LISTEN_IP", "0.0.0.0"),
    help="listen ip address",
)
parser.add_argument(
    "--port",
    type=int,
    required=False,
    default=os.getenv("LISTEN_PORT", "8080"),
    help="ephemeral port number of the server (1024 to 65535) default 8080",
)
parser.add_argument(
    "-d",
    "--devno",
    type=int,
    default=os.getenv("DEVNO", "-1"),
    help=(
        "device number for camera (typically -1=find first available,"
        " 0=internal, 1=external)"
    ),
)
parser.add_argument(
    "-n",
    "--capture-string",
    type=str,
    default=os.getenv("CAPTURE_STRING"),
    help=(
        "Any valid VideoCapture string(IP camera connection, RTSP connection"
        " string, etc"
    ),
)
parser.add_argument(
    "-c", "--confidence", type=float, default=os.getenv("CONFIDENCE", "0.3")
)
parser.add_argument("-p", "--publish", action="store_true")
parser.add_argument(
    "-s", "--sleep", type=float, default=os.getenv("SLEEP", "1.0")
)
parser.add_argument(
    "--protocol", type=str, default=os.getenv("PROTOCOL", "HTTP")
)
parser.add_argument(
    "-m",
    "--model-name",
    type=str,
    required=False,
    default=os.getenv("MODEL_NAME", "ssd_mobilenet_coco"),
    help="Name of model",
)
parser.add_argument(
    "-x",
    "--model-version",
    type=str,
    required=False,
    default=os.getenv("MODEL_VERSION", ""),
    help="Version of model. Default is to use latest version.",
)
parser.add_argument(
    "-u",
    "--triton-url",
    type=str,
    required=False,
    default=os.getenv("TRITON_URL", "localhost:8000"),
    help="Inference server URL. Default is localhost:8000.",
)
parser.add_argument(
    "--smarter-inference-url",
    type=str,
    required=False,
    default=os.getenv("SMARTER_INFERENCE_URL", ""),
    help="smarter-inferenceler URL. Default is localhost:2520.",
)
parser.add_argument(
    "-b",
    "--mqtt-broker-host",
    type=str,
    required=False,
    default=os.getenv("MQTT_BROKER_HOST", "fluent-bit"),
    help="mqtt broker host",
)
parser.add_argument(
    "--mqtt-broker-port",
    type=int,
    required=False,
    default=os.getenv("MQTT_BROKER_PORT", "1883"),
    help="port number of the mqtt server (1024 to 65535) default 1883",
)
parser.add_argument(
    "-t",
    "--mqtt-topic",
    type=str,
    required=False,
    default=os.getenv("MQTT_TOPIC", "/demo"),
    help="mqtt broker topic",
)
parser.add_argument("-db1", "--detect-car", action="store_true")
parser.add_argument("-db2", "--detect-person", action="store_true")
parser.add_argument("-db3", "--detect-bus", action="store_true")
parser.add_argument("-db4", "--detect-bicycle", action="store_true")
parser.add_argument("-db5", "--detect-motorcycle", action="store_true")
args = parser.parse_args()

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful for multiple browsers/tabs
# are viewing tthe stream)
outputFrame = None
lock = threading.Lock()

# initialize a flask object
app = Flask(__name__)

# Flask routes
@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(
        generate(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


def detection_loop():
    try:
        for img in getframe():
            detected_objects = infer_image(
                tritonclass,
                triton_client,
                endpoint_uuid,
                args.model_version,
                input_name,
                output_names,
                img,
                args.confidence,
                classes,
            )
            post_process(img, detected_objects)

            if args.sleep:
                time.sleep(args.sleep)
    except:
        os._exit(1)


def getframe():
    if args.capture_string:
        cam = cv2.VideoCapture(args.capture_string)
    else:
        cam = cv2.VideoCapture(args.devno)
    if cam.isOpened() == False:
        print(
            "Error opening video stream! Capture String:"
            f" {args.capture_string} Video devno: {args.devno}"
        )
        sys.exit(-1)
    while True:
        ret, frame = cam.read()
        if not ret:
            print("No camera found")
            sys.exit(-1)
        yield frame
    cam.release()


def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock

    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + bytearray(encodedImage)
            + b"\r\n"
        )


def log_it(sensor, label, value):
    # log something vaguely resembling waggle logs
    # timestamp,node_id,subsystem,sensor,parameter,label,value
    timestamp = (
        '"timestamp":"' + datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f") + '"'
    )
    node_id = '"nodeid":"0"'
    subsystem = '"nodeid":"0"'
    dataJson = '"' + label + '":"' + str(value) + '"'
    sensorJson = '"sensor":"' + str(sensor) + '"'
    mylist = [timestamp, node_id, subsystem, sensorJson, dataJson]
    mystr = "{" + ",".join(map(str, mylist)) + "}"
    print(mystr)
    if mqtt_client:
        mqtt_client.publish("{}/{}".format(args.mqtt_topic, label), mystr)


def annotate(img, bbox, color, thickness=2):
    cv2.rectangle(
        img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, thickness
    )


def post_process(img, detected_objects):
    # grab global references to the output frame and lock variables
    global outputFrame, lock

    if args.detect_car:
        cars = detected_objects.get("car", {})
        ncar = len(cars)
        log_it("image", "car_count", ncar)

    if args.detect_person:
        people = detected_objects.get("person", {})
        nperson = len(people)
        log_it("image", "person_count", nperson)

    if args.detect_bicycle:
        bicycles = detected_objects.get("bicycle", {})
        nbicycle = len(bicycles)
        log_it("image", "bicycle_count", nbicycle)

    if args.detect_bus:
        buses = detected_objects.get("bus", {})
        nbus = len(buses)
        log_it("image", "bus_count", nbus)

    if args.detect_motorcycle:
        motorcycles = detected_objects.get("motorcycles", {})
        nmotorcycle = len(motorcycles)
        log_it("image", "motorcycle_count", nmotorcycle)

    if args.detect_car:
        for i in range(ncar):
            bbox = cars[i]
            annotate(img, bbox, (0, 255, 0))

    if args.detect_person:
        for i in range(nperson):
            bbox = people[i]
            annotate(img, bbox, (0, 0, 255))

    if args.detect_bicycle:
        for i in range(nbicycle):
            bbox = bicycles[i]
            annotate(img, bbox, (255, 0, 0))

    if args.detect_bus:
        for i in range(nbus):
            bbox = buses[i]
            annotate(img, bbox, (255, 0, 255))

    if args.detect_motorcycle:
        for i in range(nmotorcycle):
            bbox = motorcycles[i]
            annotate(img, bbox, (0, 255, 255))

    with lock:
        outputFrame = img


def upload_model(
    url,
    model_type,
    model_name,
    model_filepath,
    model_config_filepath,
    profile_data_filepath=None,
):
    """
    Upload a model and its triton model config to the AC
    Returns status code
    """
    url = f"http://{url}/upload/{model_type}"
    req_params = {"model_name": model_name}

    upload_files = [
        ("files", open(model_filepath, "rb")),
        ("files", open(model_config_filepath, "rb")),
    ]

    if profile_data_filepath:
        upload_files.append(
            (
                "files",
                open(profile_data_filepath, "rb"),
            )
        )

    return requests.post(url, params=req_params, files=upload_files)


def load_model(
    url,
    model_name,
    load_type,
    method,
    request_batch_size=1,
    throughput_objective_weight=1,
    latency_objective_weight=1,
    latency_constraint=1,
):
    # Create a load request
    load_request = {
        "model_name": model_name,
        "load_type": load_type,
        "method": method,
        "batch_size": request_batch_size,
        "perf_targets": {
            "objectives": {
                "perf_throughput": throughput_objective_weight,
                "perf_latency": latency_objective_weight,
            },
            "constraints": {
                "perf_throughput": 1 / latency_constraint,
                "perf_latency": latency_constraint,
            },
        },
    }

    url = f"http://{url}/load"
    return requests.post(url, json=load_request)


if __name__ == "__main__":
    # open up camera
    if not args.capture_string:
        if args.devno < 0:
            video_entries = [
                entry
                for entry in os.listdir("/dev")
                if entry.startswith("video")
            ]
            if len(video_entries) == 0:
                logging.error("No cameras available")
                exit(0)
            args.devno = int(video_entries[0][len("video") :])
            print("Using entry " + str(args.devno))

    # Register MQTT client
    mqtt_client = None
    if args.publish:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(args.mqtt_broker_host, args.mqtt_broker_port, 60)
        mqtt_client.loop_start()

    classes = read_classes("ssd_mobilenet_coco.classes")

    if args.smarter_inference_url:
        # Use smarter-inference api to upload model then request to load it
        res = upload_model(
            args.smarter_inference_url,
            "tf",
            "ssd_mobilenet_coco",
            "model.graphdef",
            "config.pbtxt",
        )
        try:
            assert res.status_code in [201, 303]
        except AssertionError:
            logging.error(f"Upload model failed with response {res.text}")
            sys.exit(-1)

        print("Model upload successful")

        res = load_model(
            args.smarter_inference_url,
            "ssd_mobilenet_coco",
            "auto_gen",
            "passthrough",
            latency_constraint=args.sleep,
        )

        # endpoint_uuid holds the translated model name after loading
        # for the client to request from using the triton client api
        try:
            assert res.status_code in [201, 303]
        except AssertionError:
            logging.error(f"Load model failed with response {res.text}")
            sys.exit(-1)

        res_json = res.json()
        endpoint_uuid = res_json["request_uuid"]
        triton_url = args.smarter_inference_url.split(":")[0] + ":" + "2521"
        print(res_json["model_config"])
        print("Model load successful")
    else:
        endpoint_uuid = args.model_name
        triton_url = args.triton_url

    if args.protocol.lower() == "grpc":
        # Create gRPC client for communicating with the server
        triton_client = grpcclient.InferenceServerClient(
            url=triton_url, verbose=args.verbose
        )
    else:
        # Create HTTP client for communicating with the server
        triton_client = httpclient.InferenceServerClient(
            url=triton_url, verbose=args.verbose
        )

    # Make sure the model matches our requirements, and get some
    # properties of the model that we need for preprocessing
    try:
        model_metadata = triton_client.get_model_metadata(
            model_name=args.model_name, model_version=args.model_version
        )
    except InferenceServerException as e:
        print("failed to retrieve the metadata: " + str(e))
        sys.exit(1)

    try:
        model_config = triton_client.get_model_config(
            model_name=args.model_name, model_version=args.model_version
        )
    except InferenceServerException as e:
        print("failed to retrieve the config: " + str(e))
        sys.exit(1)

    if args.protocol.lower() == "grpc":
        input_name, output_names = validate_model_grpc(
            model_metadata, model_config.config
        )
        tritonclass = grpcclient
    else:
        input_name, output_names = validate_model_http(
            model_metadata, model_config
        )
        tritonclass = httpclient

    # Read from camera and serve flask app
    if args.flask:
        # start a thread that will perform object detection
        t = threading.Thread(target=detection_loop)
        t.start()

        # start the flask app
        app.run(
            host=args.ip,
            port=args.port,
            debug=True,
            threaded=True,
            use_reloader=False,
        )
    else:
        detection_loop()

    if args.publish:
        mqtt_client.disconnect()
