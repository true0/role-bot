import pyaudio
import wave
import numpy as np
import time
from funasr import AutoModel
import soundfile as sf
import threading
import queue

class AudioHandler:
    def __init__(self):
        # PyAudio配置
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 16000
        self.SILENCE_THRESHOLD = 0.01
        self.SILENCE_DURATION = 1.0  # 静音持续1秒认为说话结束
        
        # 初始化PyAudio
        self.p = pyaudio.PyAudio()
        
        # 初始化FunASR模型
        self.asr_model = AutoModel(model="paraformer-zh")
        
        # 用于控制音频播放的变量
        self.is_playing = False
        self.stop_playing = False
        self.audio_queue = queue.Queue()

    def is_silent(self, data):
        """检测是否为静音"""
        return np.max(np.abs(np.frombuffer(data, dtype=np.float32))) < self.SILENCE_THRESHOLD

    def record_audio(self):
        """录制音频直到检测到足够长的静音"""
        stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        print("开始录音...")
        frames = []
        silent_chunks = 0
        silent_threshold = int(self.SILENCE_DURATION * self.RATE / self.CHUNK)

        while True:
            data = stream.read(self.CHUNK)
            frames.append(data)
            
            if self.is_silent(data):
                silent_chunks += 1
                if silent_chunks > silent_threshold:
                    break
            else:
                silent_chunks = 0

        stream.stop_stream()
        stream.close()
        
        return b''.join(frames)

    def play_audio(self, audio_file):
        """播放音频文件"""
        self.stop_playing = False
        self.is_playing = True
        
        wf = wave.open(audio_file, 'rb')
        stream = self.p.open(
            format=self.p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )

        data = wf.readframes(self.CHUNK)
        while data and not self.stop_playing:
            stream.write(data)
            data = wf.readframes(self.CHUNK)

        stream.stop_stream()
        stream.close()
        wf.close()
        self.is_playing = False

    def process_audio(self):
        """主处理循环"""
        while True:
            # 录制音频
            audio_data = self.record_audio()
            
            # 如果正在播放音频，停止播放
            if self.is_playing:
                self.stop_playing = True
                while self.is_playing:
                    time.sleep(0.1)

            # 保存录音为临时文件
            with wave.open("temp.wav", 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(4)  # float32 = 4 bytes
                wf.setframerate(self.RATE)
                wf.writeframes(audio_data)

            # 进行语音识别
            result = self.asr_model.generate(input="temp.wav")
            text = result[0]['text']
            print(f"识别结果: {text}")

            # 播放反馈音频
            play_thread = threading.Thread(
                target=self.play_audio, 
                args=("response.wav",)  # 这里需要准备一个response.wav文件
            )
            play_thread.start()

    def __del__(self):
        """清理资源"""
        self.p.terminate()

if __name__ == "__main__":
    handler = AudioHandler()
    try:
        handler.process_audio()
    except KeyboardInterrupt:
        print("\n程序已停止")
