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
from triton_client import *

def read_classes(path):
  classes = {}
  with open(path) as file:
    for line in file:
      fields = line.split()
      classes[int(fields[0])] = fields[1]
  return classes

def detect(img, model_ctx, input_name, output_names, classes, target_rows, target_cols, img_rows, img_cols, confidence):
  resized = cv2.resize(img, (target_rows,target_cols))
  converted = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

  # Pass input to triton and fetch results
  result = model_ctx.run(
        { input_name : (converted,) },
        { output_names[3] : InferContext.ResultFormat.RAW,
          output_names[2] : InferContext.ResultFormat.RAW,
          output_names[1] : InferContext.ResultFormat.RAW,
          output_names[0] : InferContext.ResultFormat.RAW })

  # Iterate through detection list and print detection numbers
  detected_objects = {}
  num_detections = result[output_names[2]][0][0]
  for i in range(int(num_detections)):
    if result[output_names[1]][0][i] > confidence:
      detection_class_idx = result[output_names[3]][0][i]
      detection_class = classes[detection_class_idx]
      if detection_class not in detected_objects:
        detected_objects[detection_class] = {}

      detection_index = len(detected_objects[detection_class].keys())
      bbox = result[output_names[0]][0][i]
      left = int(bbox[1] * img_cols)
      top = int(bbox[0] * img_rows)
      right = int(bbox[3] * img_cols)
      bottom = int(bbox[2] * img_rows)

      detected_objects[detection_class][detection_index] = ( left, top, right, bottom )

  return detected_objects