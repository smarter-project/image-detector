#!/usr/bin/env python
import os
import cv2
import sys
import time
import argparse
import numpy as np
import paho.mqtt.client as mqtt
from car_person import read_model, read_classes
from car_person import img2blob, detect, log_it
from car_person import annotate

# Set env variables
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'fluent-bit')

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--devno', type=int, default=0, help='device number for camera (typically 0=internal, 1=external)')
parser.add_argument('-c', '--confidence', type=float, default=0.3)
parser.add_argument('-o', '--outfile', type=str, default=None, help='publish annotated images to outfile')
parser.add_argument('-p', '--publish', type=int, default=1, help='publish log to MQTT')
parser.add_argument('-r', '--rotate', type=float, default=0.0)
parser.add_argument('-s', '--sleep', type=float, default=1.0)
parser.add_argument('-db1', '--detect_car', action="store_true")
parser.add_argument('-db2', '--detect_person', action="store_true")
parser.add_argument('-db3', '--detect_bus', action="store_true")
parser.add_argument('-db4', '--detect_bicycle', action="store_true")
parser.add_argument('-db5', '--detect_motorcycle', action="store_true")
args = parser.parse_args()


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


client = None
if args.publish:
  client = mqtt.Client()
  client.connect(MQTT_BROKER_HOST, 1883, 60)
  client.loop_start()

model = read_model('models/ssd_mobilenet_coco.pb', 'models/ssd_mobilenet_coco.pbtxt')
classes = read_classes('models/ssd_mobilenet_coco.classes')

outfile = args.outfile
if not outfile:
  outfile = 'outfile.jpg'

p = outfile.rindex('/')
if p:
  tmp_outfile = outfile[:p+1]+'tmp_'+outfile[p+1:]
else:
  tmp_outfile = 'tmp_'+outfile

print("TMP: ", tmp_outfile)

for img in getframe(args.devno):
  img_rows = img.shape[0]
  img_cols = img.shape[1]

  if args.rotate:
    M = cv2.getRotationMatrix2D((img_cols/2, img_rows/2), args.rotate, 1)
    img = cv2.warpAffine(img, M, (img_cols, img_rows))

  blob = img2blob(img, img_rows, img_cols)

  detected_objects = detect(blob, model, classes,
                            confidence=args.confidence, 
                            img_rows=img_rows,
                            img_cols=img_cols)

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

  
  if args.outfile:
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

    cv2.imwrite(tmp_outfile, img)     # todo: write to rmq or other

    os.rename(tmp_outfile, outfile)
    
  if args.sleep:
    time.sleep(args.sleep)

if args.publish:
  client.disconnect()
