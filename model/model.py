class Model(object):
    def chat(self, message: str):
        """
        模型对话处理方法
        :return:
        """
        raise NotImplementedError

    def chat_stream(self, message: str):
        """
        模型流式对话处理方法
        :return:
        """
        raise NotImplementedError
