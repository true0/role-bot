import webrtcvad
import pyaudio

# 配置参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 320  # 每帧大小，20ms (16000Hz * 0.02s)

# 初始化 WebRTC VAD
vad = webrtcvad.Vad()
vad.set_mode(3)  # 设置敏感度，0（最低）到 3（最高）

# 初始化 PyAudio
audio = pyaudio.PyAudio()
stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

print("Listening...")

try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        # 判断是否有语音活动
        if vad.is_speech(data, RATE):
            print("User is speaking...")
        else:
            print("Silence...")
except KeyboardInterrupt:
    print("Stopping...")

stream.stop_stream()
stream.close()
audio.terminate()
