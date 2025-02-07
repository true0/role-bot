import numpy as np
import pyaudio
import torchaudio

from cosyvoice.cli.cosyvoice import CosyVoice2, CosyVoice

sampling_rate = 22050
# 初始化 PyAudio
p = pyaudio.PyAudio()

# 打开音频流
stream = p.open(format=pyaudio.paInt16,
                channels=1,  # 单声道
                rate=sampling_rate,
                output=True)
# --- CosyVoice - 语音合成模型
# cosyvoice = CosyVoice2('pretrained_models/CosyVoice-300M-25Hz')
model_dir = 'pretrained_models/CosyVoice-300M-25Hz'
# cosyvoice = CosyVoice2(model_dir) if 'CosyVoice2' in model_dir else CosyVoice(model_dir)
cosyvoice = CosyVoice(model_dir)
# --- CosyVoice - 支持的音色列表
print(cosyvoice.list_avaliable_spks())
out = cosyvoice.inference_sft('你好，这是一个语音合成示例。', '中文女', stream=False)

for o in out:
    audio_tensor = o['tts_speech']
    audio_array = audio_tensor.numpy()
    if audio_array.ndim > 1:
        audio_array = audio_array[0]
    audio_array = (audio_array * 32767).astype(np.int16)
    stream.write(audio_array.tobytes())
# 停止音频流
stream.stop_stream()
stream.close()

# 关闭 PyAudio
p.terminate()
# 保存语音
# index_out = 0
# for i, j in enumerate(cosyvoice.inference_sft('你好，这是一个语音合成示例。', '中文女', stream=False)):
#     torchaudio.save('sft_{}.wav'.format(i), j['tts_speech'], 22050)
#     index_out += 1
