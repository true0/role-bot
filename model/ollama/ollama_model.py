import ollama

from common.config import conf
from model.model import Model


class OllamaModel(Model):
    def __init__(self):
        config = conf()
        ollama_api = config['ollama_api']
        self.model_name = config['model_name']
        self.options = config['ollama_options']
        self.model = ollama.Client(host=ollama_api)

    def chat(self, message: str):
        pass

    def chat_stream(self, message: str):
        pass
