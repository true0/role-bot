from common.config import Config, conf
from voice.aliyun.aliyun_stt import AliyunSTT
from voice.tts import TTS


class DouYinVoice(TTS, AliyunSTT):
    def __init__(self, config=None):
        super().__init__()
        if config is None:
            config = conf()
        self.tts_url = config['douyin_tts_url']
        self.app_id = config['douyin_app_id']
        self.token = config['douyin_token']


if __name__ == '__main__':
    voice = DouYinVoice()
    text = voice.voice_to_text_bytes('C:\\tools\projects\python\WeChat_cli\doubao\\test\\vioce.WAV')
    print(text)
