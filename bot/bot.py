import threading


class Bot(object):
    def __init__(self):
        # 程序状态
        self.is_bot = threading.Event()
        self.message_voice = []

    def read(self):
        pass

    def write(self):
        pass
