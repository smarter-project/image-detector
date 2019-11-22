#!/usr/bin/env python

# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

from datetime import datetime
import cv2
import os


def read_model(pb_path, pbtxt_path):
  model = cv2.dnn.readNetFromTensorflow(pb_path, pbtxt_path)
  return model


def read_classes(path):
  classes = {}
  with open(path) as file:
    for line in file:
      fields = line.split()
      classes[int(fields[0])] = fields[1]
  return classes


def img2blob(img, img_rows, img_cols):
  blob = cv2.dnn.blobFromImage(
    img,
    0.00784,
    (300, 300),
    (127.5, 127.5, 127.5),
    swapRB=True,
    crop=False,
  )
  return blob


def detect(img_blob, model, classes, confidence=0.3, img_rows=1, img_cols=1):
  model.setInput(img_blob)
  cvOut = model.forward()

  output = {}
  for detection in cvOut[0, 0, :, :]:
    score = float(detection[2])
    if score > confidence:
      class_index = int(detection[1])
      class_name = classes[class_index]
      if class_name not in output:
        output[class_name] = {}

      detection_index = len(output[class_name].keys())
      left = int(detection[3] * img_cols)
      top = int(detection[4] * img_rows)
      right = int(detection[5] * img_cols)
      bottom = int(detection[6] * img_rows)

      output[class_name][detection_index] = ( left, top, right, bottom )
  return output


def log_it(client,sensor, label, value):
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
    client.publish("/demo/"+label,mystr)


def annotate(img, bbox, color, thickness=2):
  cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, thickness)


if __name__ == '__main__':
  import argparse
  import paho.mqtt.client as mqtt
  parser = argparse.ArgumentParser()
  parser.add_argument('-a', '--annotate', type=int, default=0)
  parser.add_argument('-c', '--confidence', type=float, default=0.3)
  parser.add_argument('-p', '--publish', type=int, default=1, help='publish log to MQTT')
  parser.add_argument('-r', '--rotate', type=float, default=0.0)
  parser.add_argument('images', nargs='*')
  args = parser.parse_args()

  client = None
  if args.publish:
    client = mqtt.Client()
    client.connect("fluentbit-mqtt", 1883, 60)
    client.loop_start()

  model = read_model('models/ssd_mobilenet_coco.pb', 'models/ssd_mobilenet_coco.pbtxt')
  classes = read_classes('models/ssd_mobilenet_coco.classes')

  for image_path in args.images:
    img = cv2.imread(os.path.abspath(image_path))
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

    cars = detected_objects.get('car', {})
    people = detected_objects.get('person', {})

    ncar = len(cars)
    nperson = len(people)

    log_it(client,'image', 'car_count', ncar)
    log_it(client,'image', 'person_count', nperson)

    if not args.annotate:
      continue

    for i in range(ncar):
      bbox = cars[i]
      annotate(img, bbox, (0, 255, 0))

    for i in range(nperson):
      bbox = people[i]
      annotate(img, bbox, (0, 0, 255))

    outfile = 'output-' + os.path.basename(image_path)
    cv2.imwrite(outfile, img)

  if args.publish:
    client.disconnect()
