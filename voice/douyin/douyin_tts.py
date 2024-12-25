from common.config import Config, conf
from voice.douyin.douyin_client import http_client, websocket_client
from voice.tts import TTS


class DouYinTTS(TTS):
    def __init__(self, config: Config = None):
        super().__init__()
        if config is None:
            config = conf()
        self.tts_url = config['douyin_tts_host']
        self.app_id = config['douyin_app_id']
        self.token = config['douyin_token']
        self.voice_type = config['douyin_voice_type']
        self.cluster = config['douyin_cluster']

    def text_to_voice(self, text):
        return http_client(self.tts_url, self.app_id, self.token, self.voice_type, self.cluster,
                           text)

    def text_to_voice_stream(self, text):
        return websocket_client(self.tts_url, self.app_id, self.token, self.voice_type, self.cluster, text)


if __name__ == '__main__':
    voice = DouYinTTS()
    # voice_stream = voice.text_to_voice_stream('哈哈哈，笑死我啦，假仁门谁懂啊，今天遇到了一个虾头男')
    # with open('DouBao.wav', 'wb') as wf:
    #     for tts_voice in voice_stream:
    #         wf.write(tts_voice)
