import time

import numpy as np
import pyaudio
import torch
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

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
vad_model, utils = torch.hub.load(
    repo_or_dir='C:\\tools\projects\python\\ai-bot\model\snakers4-silero-vad-46f94b7',
    model='silero_vad',
    trust_repo=None,
    source='local',
)
funasr_model = AutoModel(model="C:\\tools\projects\python\\ai-bot\model\SenseVoiceSmall",
                         vad_model="C:\\tools\projects\python\\ai-bot\model\speech_fsmn_vad_zh-cn-16k-common-pytorch",
                         vad_kwargs={"max_single_segment_time": 30000},
                         trust_remote_code=True, device="cuda:0")


def record_with_silero_vad():
    buffer = []  # 持续存储音频的缓冲区
    voice_chunk = []  # 当前检测到语音的音频片段
    silence_flag = True  # 标记是否为静音状态
    dynamic_delay = 1.5  # 动态静音延迟时间
    max_buffer_duration = 3.0  # 最大缓冲区时长（秒）
    last_confident_time = time.time()  # 上次语音检测时间
    confidence_history = []  # 用于平滑置信度
    try:
        print("start ")
        while True:
            # 读取音频数据
            audio_chunk = stream.read(num_samples)
            audio_int16 = np.frombuffer(audio_chunk, np.int16)
            audio_float32 = int2float(audio_int16)
            # 使用 Silero VAD 检测置信度
            new_confidence = vad_model(torch.from_numpy(audio_float32), 16000).item()
            confidence_history.append(new_confidence)
            if len(confidence_history) > 10:  # 滑动窗口平滑
                confidence_history.pop(0)
            avg_confidence = sum(confidence_history) / len(confidence_history)
            print("\rAverage Confidence: {:.2f}".format(avg_confidence), end="")

            # 将音频数据添加到缓冲区
            buffer.append(audio_chunk)
            if len(buffer) * 256 / 16000 > max_buffer_duration:
                buffer.pop(0)  # 保证缓冲区长度不超过最大时长

            # 语音检测逻辑
            current_time = time.time()
            if avg_confidence > 0.3:  # 检测到语音
                if silence_flag:  # 切换到语音状态
                    print("\n检测到语音，开始处理...")
                    silence_flag = False
                    last_confident_time = current_time  # 更新语音检测时间
                    voice_chunk.extend(buffer)  # 将缓冲区音频加入语音段
                    buffer.clear()  # 清空缓冲区
                last_confident_time = current_time  # 更新语音检测时间
                voice_chunk.append(audio_chunk)
            elif not silence_flag:  # 检测到静音
                time_since_last_voice = current_time - last_confident_time
                if time_since_last_voice > dynamic_delay:
                    print("\n静音结束，开始识别...")
                    # 处理当前语音段
                    audio_data = b"".join(voice_chunk)
                    result = recognition(audio_data)
                    print("语音识别结果：", result)
                    return result  # 返回完整的结果
    except Exception as e:
        print(f"发生错误: {e}")
        return ""


def recognition(input_file: bytes) -> str:
    res = funasr_model.generate(input=input_file, cache={}, language="auto", use_itn=False, batch_size_s=0,
                                disable_pbar=True)
    text = rich_transcription_postprocess(res[0]['text'])
    print("\n---->", text, "\n")


def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1 / 32768
    sound = sound.squeeze()
    return sound


if __name__ == '__main__':
    record_with_silero_vad()
