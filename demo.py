#!/usr/bin/env python
import os
import cv2
import sys
import time
import argparse
import threading
import numpy as np
import paho.mqtt.client as mqtt
from flask import Response
from flask import Flask
from flask import render_template
from detect import *
from triton_client import *

# Set env variables
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'fluent-bit')
TOPIC = os.getenv('TOPIC', '/demo')

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--flask", action="store_true", help="enable flask app")
parser.add_argument("-i", "--ip", type=str, required=False, default=os.getenv('LISTEN_IP', '0.0.0.0'),
		                help="listen ip address")
parser.add_argument("--port", type=int, required=False, default=os.getenv('LISTEN_PORT', '8080'),
		                help="ephemeral port number of the server (1024 to 65535) default 8080")
parser.add_argument('-d', '--devno', type=int, default=os.getenv('DEVNO', '-1'), help='device number for camera (typically -1=find first available, 0=internal, 1=external)')
parser.add_argument('-c', '--confidence', type=float, default=os.getenv('CONFIDENCE', '0.3'))
parser.add_argument('-p', '--publish', type=int, default=os.getenv('PUBLISH', '1'), help='publish log to MQTT')
parser.add_argument('-s', '--sleep', type=float, default=os.getenv('SLEEP', '1.0'))
parser.add_argument('--protocol', type=str, default=os.getenv('PROTOCOL', 'HTTP'))
parser.add_argument('--images', nargs='*')
parser.add_argument('-m', '--model-name', type=str, required=False, default=os.getenv('MODEL_NAME', 'ssd_mobilenet_coco'),
                    help='Name of model')
parser.add_argument('-x', '--model-version', type=int, required=False,
                    help='Version of model. Default is to use latest version.')
parser.add_argument('-u', '--url', type=str, required=False, default=os.getenv('TRITON_URL', 'localhost:8000'),
                    help='Inference server URL. Default is localhost:8000.')                
parser.add_argument('-db1', '--detect_car', action="store_true")
parser.add_argument('-db2', '--detect_person', action="store_true")
parser.add_argument('-db3', '--detect_bus', action="store_true")
parser.add_argument('-db4', '--detect_bicycle', action="store_true")
parser.add_argument('-db5', '--detect_motorcycle', action="store_true")
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
	return Response(generate(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

def getframe(devno=0):
  cam = cv2.VideoCapture(devno)
  img_counter = 0
  while True:
    ret, frame = cam.read()
    if not ret:
      print('No camera on', devno)
      exit(0)
    yield frame
  cam.release()

def detection_loop():
  for img in getframe(args.devno):
    img_rows = img.shape[0]
    img_cols = img.shape[1]
    detected_objects = detect(img, ctx, input_name, output_names, classes, h, w, img_rows, img_cols, args.confidence)
    post_process(img, args, detected_objects, client)

    if args.sleep:
      time.sleep(args.sleep)

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
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
			bytearray(encodedImage) + b'\r\n')

def log_it(client, sensor, label, value):
  # print something vaguely resembling waggle logs
  # timestamp,node_id,subsystem,sensor,parameter,label,value
  timestamp = '"timestamp":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+'"'
  node_id = '"nodeid":"0"'
  subsystem = '"nodeid":"0"' 
  dataJson = '"'+label+'":"'+str(value)+'"'
  sensorJson = '"sensor":"'+str(sensor)+'"'
  mylist = [timestamp, node_id, subsystem, sensorJson, dataJson]
  mystr = '{'+','.join(map(str, mylist))+'}'
  print(mystr)
  if client:
    client.publish("{}/{}".format(TOPIC, label), mystr)

def annotate(img, bbox, color, thickness=2):
  cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, thickness)

def post_process(img, args, detected_objects, client):
  # grab global references to the output frame and lock variables
  global outputFrame, lock

  if args.detect_car:
    cars = detected_objects.get('car', {})
    ncar = len(cars)
    log_it(client,'image', 'car_count', ncar)

  if args.detect_person:
    people = detected_objects.get('person', {})
    nperson = len(people)
    log_it(client,'image', 'person_count', nperson)

  if args.detect_bicycle:
    bicycles = detected_objects.get('bicycle', {})
    nbicycle = len(bicycles)
    log_it(client,'image', 'bicycle_count', nbicycle)

  if args.detect_bus:
    buses = detected_objects.get('bus', {})
    nbus = len(buses)
    log_it(client,'image', 'bus_count', nbus)

  if args.detect_motorcycle:
    motorcycles = detected_objects.get('motorcycles', {})
    nmotorcycle = len(motorcycles)
    log_it(client,'image', 'motorcycle_count', nmotorcycle)
  
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

if __name__ == '__main__':
  # If not using test images, open up camera
  if args.devno < 0 and not args.images:
    video_entries = [entry for entry in os.listdir("/dev") if entry.startswith("video") ]
    if len(video_entries) == 0:
      print('No cameras available')
      exit(0)
    args.devno = video_entries[0][len("video"):]
    print("Using entry " + args.devno)

  # Register MQTT client
  client = None
  if args.publish:
    client = mqtt.Client()
    client.connect(MQTT_BROKER_HOST, 1883, 60)
    client.loop_start()

  classes = read_classes('ssd_mobilenet_coco.classes')

  protocol = ProtocolType.from_str(args.protocol)

  # Fetch model information from triton server
  input_name, output_names, c, h, w, format, dtype = parse_model(
    args.url, protocol, args.model_name, 1)

  # Create model context used to pass tensors to triton
  ctx = InferContext(args.url, protocol, args.model_name, args.model_version)

  # Read from camera and serve flask app
  if args.flask:
    # start a thread that will perform object detection
    t = threading.Thread(target=detection_loop)
    t.daemon = True
    t.start()

    # start the flask app
    app.run(host=args.ip, port=args.port, debug=True,
      threaded=True, use_reloader=False)
  else:
    detection_loop()

  if args.publish:
    client.disconnect()
