import time

import numpy as np
import torch

from common.sensevoice.sensevoice import AliyunASR

vad_model, _ = torch.hub.load(
    repo_or_dir="C:\\tools\projects\python\\ai-bot\config\model\snakers4-silero-vad-46f94b7",
    model='silero_vad',
    trust_repo=None,
    source='local',
)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
v = AliyunASR()
vad_break_model = vad_model.to(device)


def record_with_silero_vad():
    """使用 Silero VAD 进行录音，使用 PyAudio 采集 16000Hz 音频"""
    import pyaudio

    # PyAudio 设置
    CHUNK = 512  # 每次读取的帧数
    FORMAT = pyaudio.paInt16  # 直接使用浮点格式，避免后续转换
    CHANNELS = 1
    RATE = 16000

    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    audio_data = b""
    is_recording = False
    try:
        confidence_history = []
        audio_buffer = []
        confidence_threshold = 0.5
        history_size = 5
        dynamic_silence_threshold = 1
        buffer_size = 20
        last_voice_time = 0

        print("开始录音...")
        while True:  # 替换原来的 call.state 判断
            try:
                # 读取音频数据
                audio_chunk = stream.read(CHUNK)
                # 将音频数据转换为numpy数组
                audio_chunk_np = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_chunk_float = audio_chunk_np.astype(np.float32) / 32768.0
                # 将当前音频片段添加到缓冲区
                audio_buffer.append(audio_chunk)
                if len(audio_buffer) > buffer_size:
                    audio_buffer.pop(0)

                # VAD检测
                input_tensor = torch.from_numpy(audio_chunk_float).float().to(device)
                confidence = vad_break_model(input_tensor, sr=RATE).item()

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
                    # 将缓冲区的音频添加到录音数据中
                    audio_data = b"".join(audio_buffer)
                    last_voice_time = current_time

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
                            # 停止录音并关闭流
                            # stream.stop_stream()
                            # stream.close()
                            # p.terminate()
                            text = v.voice_to_text_bytes(audio_data)
                            print(f"识别结果: {text}")
                            audio_data = b""
                            confidence_history.clear()
                            audio_buffer.clear()
                            # return text

            except Exception as e:
                print(f"发生错误: {e}")
                # return ""

    finally:
        # 确保资源被正确释放
        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == '__main__':
    record_with_silero_vad()
