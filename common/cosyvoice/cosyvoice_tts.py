from cli.cosyvoice import CosyVoice2
from common.config import conf
from common.tts import TTS
from utils.file_utils import load_wav
import sys

sys.path.insert(0, r'C:\tools\projects\python\role-bot\common\Matcha-TTS')


class CosyVoiceTTS(TTS):
    def __init__(self):
        super().__init__()
        config = conf()
        # self.tts_url = config['douyin_tts_host']
        # SPEAKER
        speaker = config['speaker']
        self.prompt_speaker_16k = load_wav(speaker, 16000)
        cosyvoice = CosyVoice2('pretrained_models/CosyVoice2-0.5B')

    def text_to_voice(self, text):
        pass

    def text_to_voice_stream(self, text):
        pass
