import threading
import numpy as np
import ollama
import pyaudio
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import torch

funasr_model = AutoModel(model="C:\\tools\projects\python\CC\SenseVoiceSmall",
                         vad_model="C:\\tools\projects\python\CC\speech_fsmn_vad_zh-cn-16k-common-pytorch",
                         vad_kwargs={"max_single_segment_time": 30000},
                         trust_remote_code=True, device="cuda:0")


def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1 / 32768
    sound = sound.squeeze()
    return sound


def chat_llama(message: str):
    msg = [{'role': 'system',
            'content': '请你扮演一个知识百科,用简短的回复回复内容,回答不要超过100字'},
           {'role': 'user',
            'content': f'{message}'}]
    response = ollama.Client(host='http://192.168.88.253:11434').chat(model="llama3.1:8b", messages=msg, stream=True)
    for i in response:
        yield i['message']['content']


def recognition(input_file: bytes) -> str:
    res = funasr_model.generate(input=input_file, cache={}, language="auto", use_itn=False, batch_size_s=0,
                                disable_pbar=True)
    text = rich_transcription_postprocess(res[0]['text'])
    print("\n---->", text, "\n")


if __name__ == '__main__':
    model, utils = torch.hub.load(
        repo_or_dir='C:\\tools\projects\python\\ai-bot\config\model\snakers4-silero-vad-46f94b7',
        model='silero_vad',
        trust_repo=None,
        source='local',
    )
    (get_speech_timestamps,
     save_audio,
     read_audio,
     VADIterator,
     collect_chunks) = utils
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    SAMPLE_RATE = 16000
    num_samples = 512
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=512)
    data = []
    print("Started Recording")
    audio = None
    countSize = 0
    while True:
        audio_chunk = stream.read(num_samples)
        audio_int16 = np.frombuffer(audio_chunk, np.int16)
        audio_float32 = int2float(audio_int16)
        new_confidence = model(torch.from_numpy(audio_float32), 16000).item()
        if new_confidence > 0.5:
            if audio is None:
                audio = audio_chunk
                countSize = 0
            else:
                audio = audio + audio_chunk
                countSize = 0
        else:
            countSize = countSize + 1
            if audio is not None and countSize < 3:
                audio = audio + audio_chunk
            elif audio is not None and countSize > 3:
                t = threading.Thread(target=recognition, args=(audio,), name='LoopThread')
                t.start()
                audio = None
                countSize = 0
