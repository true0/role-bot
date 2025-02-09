import re
import threading
import time
from queue import Queue, Empty
from threading import Lock
import numpy as np
import ollama
import pyaudio
import torch
from bot import Bot
from common.config import conf
from common.message import Message
from common.sensevoice.sensevoice import AliyunASR

FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK_SIZE = 512


class OllamaBot(Bot):
    def __init__(self):
        config = conf()
        self.model_name = config['model_name']
        self.model_api = config['ollama_api']
        p = pyaudio.PyAudio()
        # self.messages = Message(sys_prompt='请你扮演一个知识百科,用简短的回复回复内容,回答不要超过100字')
        self.messages = Message()
        # 程序运行状态
        self.running = True
        # 是否正在说话
        self.speak = False
        # 存储生成的音频
        self.output_voice = Queue()
        # 存储识别的文本
        self.input_text = Queue()
        # 打断锁
        self.speak_lock = Lock()
        # 初始化输入输出
        self.bot_inp = p.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=SAMPLE_RATE,
                              input=True,
                              frames_per_buffer=CHUNK_SIZE)
        self.bot_out = p.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=SAMPLE_RATE,
                              output=True)
        # ASR
        self.asr = AliyunASR()
        # 播音线程
        self.bot_write = threading.Thread(target=self.write, daemon=True)
        # 录音线程
        self.bot_read = threading.Thread(target=self.read, daemon=True)
        # 模型生成与音频生成线程
        self.bot_chat = threading.Thread(target=self.chat, daemon=True)
        # VAD
        vad_path = config['vad_path']
        vad_model, _ = torch.hub.load(
            repo_or_dir=vad_path,
            model='silero_vad',
            trust_repo=None,
            source='local',
        )
        # 设备配置
        # self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.vad_device = config['vad_device']
        self.vad_break_model = vad_model.to(self.vad_device)
        self.asr_lock = Lock()  # 添加ASR锁
        self.queue_timeout = 1  # 设置队列超时时间
        self.asr_timeout = 10  # 设置ASR超时时间

    def set_speak(self, value):
        with self.speak_lock:
            self.speak = value

    def is_speaking(self):
        with self.speak_lock:
            return self.speak

    def cleanup(self):
        print("开始清理资源...")
        self.running = False
        # 清空队列
        for q in [self.input_text, self.output_voice]:
            while not q.empty():
                try:
                    q.get_nowait()
                except Empty:
                    pass

    def start(self):
        print("程序运行...")
        self.running = True
        self.bot_write.start()
        self.bot_chat.start()
        self.bot_read.start()
        while self.running:
            time.sleep(2)
        print("程序结束...")

    def write(self):
        while self.running:
            try:
                if self.bot_out.is_active():
                    out_voice = self.output_voice.get_nowait()  # 使用非阻塞获取
                    print("播放音频---->", out_voice)
                else:
                    time.sleep(0.3)  # 添加短暂休眠
            except Empty:
                continue
            except Exception as e:
                print(f"Write error: {e}")

    def read(self):
        audio_data = b""
        is_recording = False
        confidence_history = []
        audio_buffer = []
        confidence_threshold = 0.5
        history_size = 5
        dynamic_silence_threshold = 1
        buffer_size = 20
        last_voice_time = 0
        print("开始录音...")
        while self.running:
            try:
                # 读取音频数据
                audio_chunk = self.bot_inp.read(CHUNK_SIZE)
                # 将音频数据转换为numpy数组
                audio_chunk_np = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_chunk_float = audio_chunk_np.astype(np.float32) / 32768.0
                # 将当前音频片段添加到缓冲区
                audio_buffer.append(audio_chunk)
                if len(audio_buffer) > buffer_size:
                    audio_buffer.pop(0)

                # VAD检测
                input_tensor = torch.from_numpy(audio_chunk_float).float().to(self.vad_device)
                confidence = self.vad_break_model(input_tensor, sr=SAMPLE_RATE).item()

                # 使用滑动窗口平滑置信度
                confidence_history.append(confidence)
                if len(confidence_history) > history_size:
                    confidence_history.pop(0)
                avg_confidence = sum(confidence_history) / len(confidence_history)

                print(f"\r当前置信度: {avg_confidence:.4f}", end="")

                current_time = time.time()

                # 基于平均置信度决定是否录音
                if avg_confidence > confidence_threshold and not is_recording:
                    print("\n检测到语音，开始录音...")
                    is_recording = True
                    self.set_speak(True)
                    # 将缓冲区的音频添加到录音数据中
                    audio_data = b"".join(audio_buffer)
                    last_voice_time = current_time
                    if self.bot_out.is_active():
                        self.bot_out.stop_stream()

                if is_recording:
                    audio_data += audio_chunk

                    # 更新最后一次检测到声音的时间
                    if avg_confidence > confidence_threshold:
                        last_voice_time = current_time

                    # 检查是否需要停止录音
                    silence_duration = current_time - last_voice_time
                    if avg_confidence < confidence_threshold and silence_duration > dynamic_silence_threshold:
                        print(f"\n检测到持续静音 {silence_duration:.1f} 秒，停止录音...")
                        is_recording = False
                        if len(audio_data) > 0:
                            print("开始识别...")
                            with self.asr_lock:  # 添加锁保护
                                text = self.asr.voice_to_text_bytes(audio_data)
                                if text.strip():  # 只有当识别出有效文本时才加入队列
                                    self.input_text.put(text)
                            print(f"识别结果: {text}")
                        audio_data = b""
                        confidence_history.clear()
                        audio_buffer.clear()
                        self.set_speak(False)
                        if not self.bot_out.is_active():
                            self.bot_out.start_stream()
            except Exception as e:
                print(f"发生错误: {e}")

    def chat(self):
        while self.running:
            try:
                if not self.input_text.empty():
                    out_text = self.input_text.get_nowait()  # 使用非阻塞获取
                    self.messages.add_query(out_text)
                    printed_sentences = list()
                    response = self.chat_llama(self.messages.messages)
                    for text in response:
                        if not self.running or not self.bot_out.is_active():
                            break
                        printed_sentences.append(text)
                        self.output_voice.put(text)
                    print("模型已回复---->", ''.join(printed_sentences))
                    self.messages.add_reply(''.join(printed_sentences))
                    printed_sentences.clear()
                else:
                    time.sleep(0.3)  # 添加短暂休眠，减少CPU占用
            except Empty:
                continue
            except Exception as e:
                print(f"Chat error: {e}")

    def chat_llama(self, history: list):
        try:
            print(history)
            print(self.model_api, self.model_name)
            response = ollama.Client(host=self.model_api).chat(model=self.model_name, messages=history, stream=True,
                                                               options={"top_p": 0.9})
            buffer = ""
            for chunk in response:
                if content := chunk['message']['content']:
                    buffer += content
                    while match := re.search(r'[^，。！？]*[，。！？]', buffer):
                        yield match.group()
                        buffer = buffer[match.end():]
            if buffer.strip():
                yield buffer
        except ollama.ResponseError as e:
            print('Error:', e.error)


if __name__ == '__main__':
    OllamaBot().start()
