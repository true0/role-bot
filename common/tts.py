class TTS(object):
    def text_to_voice(self, text):
        """
        Send text to voice service and get voice
        """
        raise NotImplementedError

    def text_to_voice_stream(self, text):
        """
        Send text to voice service and get voice
        """
        raise NotImplementedError
