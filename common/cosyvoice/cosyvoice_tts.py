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
        speaker = config['speaker_audio']
        cosyvoice_model = config['cosyvoice_model']
        self.speaker_prompt = config['speaker_prompt']
        self.prompt_speaker_16k = load_wav(speaker, 16000)
        self.cosyvoice = CosyVoice2(cosyvoice_model)

    def text_to_voice(self, text):
        for _, j in enumerate(self.cosyvoice.inference_zero_shot(
                text, self.speaker_prompt, self.prompt_speaker_16k, stream=False)):
            return j['tts_speech']

    def text_to_voice_stream(self, text):
        for j in self.cosyvoice.inference_zero_shot(
                text, self.speaker_prompt, self.prompt_speaker_16k, stream=True):
            yield j['tts_speech']
