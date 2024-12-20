import configparser
import os


class Config:
    def __init__(self, file_name: str = "config/config.ini", encoding: str = "utf-8"):
        """
        初始化配置类。

        :param file_name: 配置文件路径，相对于项目根目录。
        :param encoding: 配置文件编码。
        """
        # 获取配置文件完整路径
        self.config_file_path = self.get_config_file_path(file_name)
        # 初始化配置并设置默认值
        self.config = self.config_init(self.config_file_path, encoding)

    @staticmethod
    def get_config_file_path(file_name: str):
        """
        获取配置文件的完整路径。

        :param file_name: 配置文件名。
        :return: 配置文件的完整路径。
        """
        # 获取当前文件的目录路径（common 文件夹）
        common_dir = os.path.dirname(os.path.abspath(__file__))
        # 向上导航到项目根目录
        project_root = os.path.dirname(common_dir)
        # 构建到配置文件的完整路径
        return os.path.join(project_root, file_name)

    def config_init(self, file_name: str, encoding: str):
        """
        初始化配置，并设置默认值。

        :param file_name: 配置文件名。
        :param encoding: 配置文件编码。
        :return: 配置解析器对象。
        """
        # 默认配置值
        default_values = {
            # 示例
            # 'TTS': {
            #     'config_path': './config/tts/ZHconfig.json',
            #     'ckpt_path': './config/tts/爱小静.pth',
            #     'speed': 1.1,
            #     'device': 'cuda:0'
            # },
        }

        # 创建配置解析器对象
        config = configparser.ConfigParser()
        try:
            # 尝试读取配置文件
            config.read(file_name, encoding=encoding)
        except configparser.Error as e:
            # 如果读取配置文件出错，打印错误信息
            print(f"Error reading config file: {e}")

        # 遍历默认配置，确保所有默认值都已设置
        for section, values in default_values.items():
            if not config.has_section(section):
                config.add_section(section)
            for key, value in values.items():
                if not config.has_option(section, key):
                    config.set(section, key, str(value))
        return config

    def get(self, section, option, fallback=None):
        """
        获取配置项的值。

        :param section: 配置节。
        :param option: 配置项。
        :param fallback: 如果配置项不存在，返回的默认值。
        :return: 配置项的值。
        """
        return self.config.get(section, option, fallback=fallback)

    def getint(self, section, option, fallback=0):
        """
        获取配置项的整数值。

        :param section: 配置节。
        :param option: 配置项。
        :param fallback: 如果配置项不存在，返回的默认整数值。
        :return: 配置项的整数值。
        """
        return self.config.getint(section, option, fallback=fallback)

    def getfloat(self, section, option, fallback=0.0):
        """
        获取配置项的浮点数值。

        :param section: 配置节。
        :param option: 配置项。
        :param fallback: 如果配置项不存在，返回的默认浮点数值。
        :return: 配置项的浮点数值。
        """
        return self.config.getfloat(section, option, fallback=fallback)

    def getboolean(self, section, option, fallback=False):
        """
        获取配置项的布尔值。

        :param section: 配置节。
        :param option: 配置项。
        :param fallback: 如果配置项不存在，返回的默认布尔值。
        :return: 配置项的布尔值。
        """
        return self.config.getboolean(section, option, fallback=fallback)

    def get_path(self, section, option, fallback=""):
        """
        获取配置项的路径值，并将其转换为绝对路径。

        :param section: 配置节。
        :param option: 配置项。
        :param fallback: 如果配置项不存在，返回的默认路径。
        :return: 配置项的绝对路径。
        """
        path = self.get(section, option, fallback)
        return os.path.abspath(path) if path else path
