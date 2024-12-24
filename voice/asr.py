class ASR(object):
    def voice_to_text_file(self, voice_file) -> str:
        """
        Send voice to voice service and get text
        """
        raise NotImplementedError

    def voice_to_text_bytes(self, voice_bytes) -> str:
        """
        Send voice to voice service and get text
        """
        raise NotImplementedError
