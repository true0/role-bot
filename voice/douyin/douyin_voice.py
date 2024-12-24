from common.config import Config, conf
from voice.voice import Voice


class DouYinVoice(Voice):
    def __init__(self, config=None):
        if config is None:
            config = conf()
        self.url = config['douyin']['url']
