import numpy as np
import cv2


def validate_model_http(model_metadata, model_config):
    """
    Check the configuration of a model to make sure it meets the
    requirements for ssd_mobilenet_v1 (as expected by
    this client)
    """
    if len(model_metadata['inputs']) != 1:
        raise Exception("expecting 1 input, got {}".format(
            len(model_metadata['inputs'])))
    if len(model_metadata['outputs']) != 4:
        raise Exception("expecting 4 outputs, got {}".format(
            len(model_metadata['outputs'])))

    if len(model_config['input']) != 1:
        raise Exception(
            "expecting 1 input in model configuration, got {}".format(
                len(model_config['input'])))

    for output_metadata in model_metadata['outputs']:
        if output_metadata['datatype'] != "FP32":
            raise Exception("expecting output datatype to be FP32, model '" +
                            model_metadata['name'] + "' output type is " +
                            output_metadata['datatype'])

    return model_metadata['inputs'][0]['name'], [output['name'] for output in model_metadata['outputs']]


def validate_model_grpc(model_metadata, model_config):
    """
    Check the configuration of a model to make sure it meets the
    requirements for ssd_mobilenet_v1 (as expected by
    this client)
    """
    if len(model_metadata.inputs) != 1:
        raise Exception("expecting 1 input, got {}".format(
            len(model_metadata.inputs)))
    if len(model_metadata.outputs) != 4:
        raise Exception("expecting 4 outputs, got {}".format(
            len(model_metadata.outputs)))

    if len(model_config.input) != 1:
        raise Exception(
            "expecting 1 input in model configuration, got {}".format(
                len(model_config.input)))

    for output_metadata in model_metadata.outputs:
        if output_metadata.datatype != "FP32":
            raise Exception("expecting output datatype to be FP32, model '" +
                            model_metadata.name + "' output type is " +
                            output_metadata.datatype)

    return model_metadata.inputs[0].name, [output.name for output in model_metadata.outputs]


def read_classes(path):
    classes = {}
    with open(path) as file:
        for line in file:
            fields = line.split()
            classes[int(fields[0])] = fields[1]
    return classes


def infer_image(
        clientclass, client, model_name, model_version, input_name, output_names, imgorig, confidence, classes,
        armnn=False):
    img_rows = imgorig.shape[0]
    img_cols = imgorig.shape[1]
    resized = cv2.resize(imgorig, (300, 300))
    converted = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    
    if armnn:
      converted = ((np.asarray(converted)/255.0) * 2.0) - 1  # normalize values
      converted = np.expand_dims(converted, axis=0)

    # create input
    request_input = clientclass.InferInput(
        input_name, [1, 300, 300, 3], "FP32")
    if armnn:
        request_input.set_data_from_numpy(
            converted.astype(np.float32))
    else:
        request_input.set_data_from_numpy(
            converted)

    # create output
    detection_boxes_request = clientclass.InferRequestedOutput(
        output_names[0])
    detection_classes_request = clientclass.InferRequestedOutput(
        output_names[1])
    detection_probs_request = clientclass.InferRequestedOutput(
        output_names[2])
    num_detections_request = clientclass.InferRequestedOutput(
        output_names[3])

    results = client.infer(model_name, (request_input,), model_version=model_version, outputs=(
        detection_boxes_request, detection_classes_request, detection_probs_request, num_detections_request))

    detection_boxes = results.as_numpy(output_names[0])
    detection_classes = results.as_numpy(output_names[1])
    detection_probs = results.as_numpy(output_names[2])
    num_detections = results.as_numpy(output_names[3])

    # Iterate through detection list and print detection numbers
    detected_objects = {}
    for i in range(int(num_detections[0])):
        if detection_probs[0][i] > confidence:
            detection_class_idx = detection_classes[0][i]

            # For some reason after converting ssd_mobilenet_v1 to tflite and then armnn the detection classes
            # shift by one
            detection_class = classes[detection_class_idx + 1] if armnn else classes[detection_class_idx]
            if detection_class not in detected_objects:
                detected_objects[detection_class] = {}
            detection_index = len(detected_objects[detection_class].keys())
            bbox = detection_boxes[0][i]
            left = int(bbox[1] * img_cols)
            top = int(bbox[0] * img_rows)
            right = int(bbox[3] * img_cols)
            bottom = int(bbox[2] * img_rows)

            detected_objects[detection_class][detection_index] = (
                left, top, right, bottom)

    return detected_objects
