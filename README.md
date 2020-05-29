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

For arguments see demo.py
