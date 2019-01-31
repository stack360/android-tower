import mongoengine
import pika
import simplejson as json
import time

from datetime import datetime
from flask import current_app as app
from flask import Blueprint, request

import utils
from models import models

api = Blueprint('api', __name__, template_folder='templates')

def _build_error(error_code, message):
    return {"status_code": error_code, "data": message}


def _get_request_args(**kwargs):
    args = dict(request.args)
    for key, value in args.items():
        converter = kwargs[key]
        if isinstance(value, list):
            args[key] = [converter(item) for item in value]
        else:
            args[key] = converter(value)
    return args


@api.route('/api/devices', methods=['GET'])
def list_devices():
    devices = models.Device.objects.order_by('-last_updated')
    devices = [d.to_dict() for d in devices]
    return utils.make_json_response(200, devices)


@api.route('/api/devices/<string:device_id>', methods=['GET'])
def get_device_info(device_id):
    device, error = _get_device_by_id(device_id)
    if error:
        return utils.make_json_response(**error)
    return utils.make_json_response(200, device.to_dict())


@api.route('/api/devices', methods=['POST'])
def register_device():
    data = utils.get_request_data()

    device = models.Device()
    try:
        device.name = data['name']
    except KeyError:
        return utils.make_json_response(
            400,
            "Error registering device: device name not found."
        )
    device.last_updated = datetime.now()
    try:
        device.save()
    except mongoengine.errors.NotUniqueError as e:
        return utils.make_json_response(409, str(e))
    return utils.make_json_response(200, device.to_dict())


@api.route('/api/devices/<string:device_id>', methods=['DELETE'])
def unregister_device(device_id):
    device, error = _get_device_by_id(device_id)
    if error:
        return utils.make_json_response(**error)
    device_name = device.name
    device.delete()
    return utils.make_json_response(
        200,
        {"name": device_name, "status": "deleted"}
    )


@api.route('/api/run_function', methods=['POST'])
def run_function():
    data = utils.get_request_data()
    device = _select_device()
    if not device:
        return utils.make_json_response(
            400,
            "Bad Request: No device available."
        )
    code, status = _send_function_trigger(device.name, data)
    if code == 200:
        device.last_triggered = datetime.now()
        device.save()
    return utils.make_json_response(code, status)


def _select_device():
    devices = models.Device.objects.order_by('-last_triggered')
    if not devices:
        return None
    selected_device = devices[len(devices) - 1]
    return selected_device


def _send_function_trigger(device_name, data):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=app.config['RABBIT_HOST'], port=5672)
    )
    channel = connection.channel()
    channel.queue_declare(queue=device_name)
    payload = json.dumps(data)
    channel.basic_publish(exchange='',
                          routing_key=device_name,
                          body=payload)
    connection.close()
    return 200, "function triggered."

def _get_device_by_id(device_id):
    try:
        device = models.Device.objects.get(id=device_id)
    except mongoengine.errors.ValidationError as e:
        return None, _build_error(400, e.__str__())
    except models.Device.DoesNotExist as e:
        return None, _build_error(404, e.__str__())
    return device, None
