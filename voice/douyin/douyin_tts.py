from common.config import Config, conf
from voice.tts import TTS


class DouYinTTS(TTS):
    def __init__(self, config: Config = None):
        super().__init__()
        if config is None:
            config = conf()
        self.tts_url = config['douyin_tts_url']
        self.app_id = config['douyin_app_id']
        self.token = config['douyin_token']
        self.voice_type = config['douyin_voice_type']

    def text_to_voice(self, text, ):
        print(text)

    def text_to_voice_stream(self, text):
        print(text)


if __name__ == '__main__':
    voice = DouYinTTS()
    voice.text_to_voice('hello')
