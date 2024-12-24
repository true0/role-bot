class Voice(object):
    def voice_to_text_file(self, voice_file):
        """
        Send voice to voice service and get text
        """
        raise NotImplementedError

    def voice_to_text_bytes(self, voice_bytes):
        """
        Send voice to voice service and get text
        """
        raise NotImplementedError

    def text_to_voice(self, text):
        """
        Send text to voice service and get voice
        """
        raise NotImplementedError
