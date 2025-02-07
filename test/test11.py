import threading
import queue
import librosa
import numpy as np
import pyaudio
import torch
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.common import set_all_random_seed
from cosyvoice.utils.file_utils import load_wav

max_val = 0.8


def postprocess(speech, top_db=60, hop_length=220, win_length=440):
    speech, _ = librosa.effects.trim(
        speech, top_db=top_db,
        frame_length=win_length,
        hop_length=hop_length
    )
    if speech.abs().max() > max_val:
        speech = speech / speech.abs().max() * max_val
    speech = torch.concat([speech, torch.zeros(1, int(cosyvoice.sample_rate * 0.2))], dim=1)
    return speech


sampling_rate = 16000
# 初始化 PyAudio
p = pyaudio.PyAudio()
# 打开音频流
stream = p.open(format=pyaudio.paInt16,
                channels=1,  # 单声道
                rate=22050,
                output=True)
model_dir = 'pretrained_models/CosyVoice2-0.5B'
prompt_wav = "q3.wav"
prompt_text = '哈哈哈，笑死我啦，假仁门谁懂啊，今天遇到了一个虾头男'
seed = 0
speed = 1
tts_text = '懂点常识的人都知道，人死后十小时内在常温环境下，一个小时大概会下降一度，经过24小时之后体温才会和环境基本接近，但是那老人的体温在我看来却低于常温至少十度，甚至还要更多，而当时晚上的气温是二十二度。'
cosyvoice = CosyVoice2(model_dir)
# --- CosyVoice - 支持的音色列表
prompt_speech_16k = postprocess(load_wav(prompt_wav, sampling_rate))
set_all_random_seed(seed)

# 创建一个队列用于存储音频数据
audio_queue = queue.Queue()


# 用于播放音频的线程函数
def play_audio():
    while True:
        # 从队列中获取音频数据
        audio_data = audio_queue.get()
        if audio_data is None:  # 使用 None 作为结束信号
            break
        # 将音频数据转换为 16 位 PCM 格式
        audio_data_16bit = (audio_data * 32767).astype(np.int16)
        # 将音频数据写入音频流
        stream.write(audio_data_16bit.tobytes())
        # 标记任务完成
        audio_queue.task_done()


# 创建并启动音频播放线程
audio_thread = threading.Thread(target=play_audio)
audio_thread.start()

# 主线程生成音频数据并放入队列
for i in cosyvoice.inference_zero_shot(tts_text, prompt_text, prompt_speech_16k, stream=True, speed=speed):
    voice_data = i['tts_speech']
    # 将音频数据转换为 NumPy 数组
    audio_data = voice_data.numpy().flatten()
    # 将音频数据放入队列
    audio_queue.put(audio_data)

# 等待队列中的所有任务完成
audio_queue.join()

# 向队列发送结束信号
audio_queue.put(None)

# 等待音频播放线程结束
audio_thread.join()

# 停止音频流
stream.stop_stream()
stream.close()

# 关闭 PyAudio
p.terminate()
