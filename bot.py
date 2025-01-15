class Bot(object):

    def read(self):
        """
        录制声音的线程
        :return:
        """
        raise NotImplementedError

    def write(self):
        """
        播放声音的线程
        :return:
        """
        raise NotImplementedError
