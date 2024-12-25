import asyncio
import base64
import gzip
import json
import queue
import threading
import uuid

import websockets

from common.log import logger

import requests

MESSAGE_TYPES = {
    11: "audio-only server response",
    12: "frontend server response",
    15: "error message from server"
}
MESSAGE_TYPE_SPECIFIC_FLAGS = {
    0: "no sequence number",
    1: "sequence number > 0",
    2: "last message from server (seq < 0)",
    3: "sequence number < 0"
}
MESSAGE_SERIALIZATION_METHODS = {
    0: "no serialization",
    1: "JSON",
    15: "custom type"
}
MESSAGE_COMPRESSIONS = {
    0: "no compression",
    1: "gzip",
    15: "custom compression method"
}
default_header = bytearray(b'\x11\x10\x11\x00')


def get_request(appid, token, cluster, voice_type, text="", operation="submit", rate=16000, encoding='pcm',
                speed_ratio=1,
                uid=str(uuid.uuid4())):
    return {
        "app": {
            "appid": appid,
            "token": token,
            "cluster": cluster
        },
        "user": {
            "uid": uid
        },
        "audio": {
            "rate": rate,
            "voice_type": voice_type,
            "encoding": encoding,
            "speed_ratio": speed_ratio,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": uid,
            "text": text,
            "text_type": "plain",
            "operation": operation
        }
    }


def get_request_protocol(request_json):
    payload_bytes = str.encode(json.dumps(request_json))
    payload_bytes = gzip.compress(payload_bytes)
    full_client_request = bytearray(default_header)
    full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
    full_client_request.extend(payload_bytes)
    return full_client_request


def http_client(url, appid, token, voice_type, cluster, text):
    header = {"Authorization": f"Bearer;{token}"}
    api_url = f"https://{url}/api/v1/tts"
    try:
        resp = requests.post(api_url, json.dumps(
            get_request(appid, token, cluster, voice_type, text, operation="query", encoding='wav')),
                             headers=header)
        if "data" in resp.json():
            data = resp.json()["data"]
            logger.info("抖音tts合成成功")
            # file_to_save = open("./test.wav", "wb")
            # file_to_save.write(base64.b64decode(data))
            return base64.b64decode(data)
    except Exception as e:
        logger.error("抖音tts合成失败", e)


async def get_tts(url, appid, token, voice_type, cluster, text):
    header = {"Authorization": f"Bearer; {token}"}
    api_url = f"wss://{url}/api/v1/tts/ws_binary"
    async with websockets.connect(api_url, extra_headers=header, ping_interval=None) as ws:
        await ws.send(get_request_protocol(
            get_request(appid, token, cluster, voice_type, text, encoding='wav')))
        while True:
            res = await ws.recv()
            done, payload = parse_response(res)
            if payload:
                yield payload
            if done:
                break


def parse_response(res):
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    message_compression = res[2] & 0x0f
    payload = res[header_size * 4:]
    if message_type == 0xb:
        if message_type_specific_flags == 0:
            return False, None
        else:
            sequence_number = int.from_bytes(payload[:4], "big", signed=True)
            payload = payload[8:]
        is_end = sequence_number < 0
        return is_end, payload
    elif message_type == 0xf:
        code = int.from_bytes(payload[:4], "big", signed=False)
        msg_size = int.from_bytes(payload[4:8], "big", signed=False)
        error_msg = payload[8:]
        if message_compression == 1:
            error_msg = gzip.decompress(error_msg)
        error_msg = str(error_msg, "utf-8")
        logger.info("code:{},size:{},message".format(code, msg_size, error_msg))
        return True, None
    elif message_type == 0xc:
        payload = payload[4:]
        if message_compression == 1:
            payload = gzip.decompress(payload)
        logger.info(f"Frontend message: {payload}")
    else:
        logger.error("undefined message type!")
        return True, None


def websocket_client(url, appid, token, voice_type, cluster, text):
    q = queue.Queue()
    stop_event = threading.Event()

    def run_async():
        async def produce_audio():
            try:
                async for chunk in get_tts(url, appid, token, voice_type, cluster, text):
                    q.put(chunk)
            finally:
                stop_event.set()

        asyncio.run(produce_audio())

    thread = threading.Thread(target=run_async)
    thread.start()
    while not stop_event.is_set() or not q.empty():
        try:
            yield q.get(timeout=0.1)
        except queue.Empty:
            continue
