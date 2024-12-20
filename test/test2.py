import re
import threading
import numpy as np
import ollama
import pyaudio
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import torch
from melo.api import TTS

speed = 1.1
device = 'cuda:0'

config_path = "C:\\tools\projects\python\CC\ZHconfig.json"
ckpt_path = "C:\\tools\projects\python\CC\爱小静.pth"
modelTTs = TTS(language='ZH', config_path=config_path, ckpt_path=ckpt_path, device="cuda:0")
speaker_ids = modelTTs.hps.data.spk2id
modelTTs.tts_to_file("预启动", speaker_ids['ZH'], speed=speed, sdp_ratio=0.6, noise_scale=0.6)
# 初始化模型
funasr_model = AutoModel(model="C:\\tools\projects\python\CC\SenseVoiceSmall",
                         vad_model="C:\\tools\projects\python\CC\speech_fsmn_vad_zh-cn-16k-common-pytorch",
                         vad_kwargs={"max_single_segment_time": 30000},
                         trust_remote_code=True, device="cuda:0")

# Silero VAD模型初始化
model, utils = torch.hub.load(
    repo_or_dir='C:/tools/projects/python/cc-server/vadTest/silero-vad',
    model='silero_vad',
    trust_repo=None,
    source='local',
)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK_SIZE = 512

p = pyaudio.PyAudio()
message = []
speak = False


def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1 / 32768
    return sound


def chat_llama(message: str):
    msg = [{'role': 'system', 'content': '请你扮演一个知识百科,用简短的回复回复内容,回答不要超过100字'},
           {'role': 'user', 'content': f'{message}'}]
    response = ollama.Client(host='http://192.168.88.253:11434').chat(model="llama3.1:8b", messages=msg, stream=True)
    for i in response:
        yield i['message']['content']


def get_voice(text):
    dates = modelTTs.tts_to_file(text, speaker_ids['ZH'], speed=speed, sdp_ratio=0.6, noise_scale=0.6)
    audio = np.int16(dates * 32767)
    return audio.tobytes()


def recognition(input_file: bytes):
    try:
        res = funasr_model.generate(input=input_file, cache={}, language="auto", use_itn=False, batch_size_s=0,
                                    disable_pbar=True)
        text = rich_transcription_postprocess(res[0]['text'])
        print("\n---->", text, "\n")
        if text:
            printed_sentences = set()
            buffer = str()
            for i in chat_llama(text):
                if speak:
                    message.clear()
                    break
                buffer += i
                sentences = re.split('([，。！？])', buffer)
                for j in range(0, len(sentences) - 1, 2):

                    sentence = sentences[j] + sentences[j + 1]
                    if sentence not in printed_sentences:
                        try:
                            voice = get_voice(sentence)
                            if speak:
                                message.clear()
                                break
                            message.append(voice)
                        except Exception as e:
                            print("合成错误", e)
                        printed_sentences.add(sentence)
    except Exception as e:
        print(f"Recognition error: {e}")


def audio_callback(in_data, frame_count, time_info, status):
    global speak, play

    audio_int16 = np.frombuffer(in_data, np.int16)
    audio_float32 = int2float(audio_int16)
    new_confidence = model(torch.from_numpy(audio_float32), 16000).item()

    if new_confidence > 0.5:
        # 用户开始说话时，清空音频队列并停止当前播放
        speak = True
        message.clear()  # 清空剩余未播放的音频
        play.stop_stream()  # 停止音频播放

        if not hasattr(audio_callback, 'audio'):
            audio_callback.audio = in_data
        else:
            audio_callback.audio += in_data
    else:
        if hasattr(audio_callback, 'audio'):
            speak = False
            # 启动新线程进行语音识别
            t = threading.Thread(target=recognition, args=(audio_callback.audio,), name='RecognitionThread')
            t.start()
            del audio_callback.audio

    return (in_data, pyaudio.paContinue)


stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=audio_callback)
play = p.open(format=FORMAT,
              channels=CHANNELS,
              rate=44100,
              output=True)
print("Started Recording")
stream.start_stream()

# 主播放线程部分
try:
    while stream.is_active():
        # 主线程处理音频播放
        if message:
            if speak:  # 如果用户说话，跳过播放
                message.clear()  # 清空未播放的音频
                continue
            print("播放音频")
            if not play.is_active():
                play.start_stream()  # 确保音频流已启动
            play.write(message.pop(0))  # 播放当前音频片段
except KeyboardInterrupt:
    # 处理用户中断
    pass
finally:
    stream.stop_stream()
    stream.close()
    play.stop_stream()
    play.close()
    p.terminate()
    print("Stopped Recording")
