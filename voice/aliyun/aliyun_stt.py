from funasr.utils.postprocess_utils import rich_transcription_postprocess

from common.config import Config, conf
from voice.stt import STT
from funasr import AutoModel


class AliyunSTT(STT):
    """
    SenseVoiceSmall开源语音识别模型
    识别不是很准
    """
    def __init__(self, config=None):
        if config is None:
            config = conf()
        funasr_model_path = config['funasr_model']
        funasr_vad_model = config['funasr_vad_model']
        funasr_device = config['funasr_device']
        self.funasr_model = AutoModel(model=funasr_model_path,
                                      vad_model=funasr_vad_model,
                                      vad_kwargs={"max_single_segment_time": 30000},
                                      trust_remote_code=True,
                                      device=funasr_device)

    def voice_to_text_file(self, voice_file):
        return self.voice_to_text_bytes(voice_file)

    def voice_to_text_bytes(self, voice_bytes):
        res = self.funasr_model.generate(input=voice_bytes, cache={}, language="zh", use_itn=False, batch_size_s=0,
                                         disable_pbar=True)
        # return rich_transcription_postprocess(res[0]['text'])
        # print(res)
        text = res[0]['text'].replace(" ", "")
        return text
