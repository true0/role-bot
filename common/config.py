import json
import os
from typing import Any, Dict

from common.log import logger

# 配置可用的默认设置
available_setting = {
    # 身份提示词
    "sys_prompt": "",

    # 模型配置
    # 模型名称
    "model_name": "",
    # 模型流式
    "model_stream": False,
    # ollama_api
    "ollama_api": "",
    # ollama_options
    "ollama_options": {},  # 与官方一致

    # 识别配置
    # VAD模型路径
    "vad_path": "",
    "vad_device": "",
    # SenseVoiceSmall开源识别模型
    "funasr_model": "",  # 模型地址
    "funasr_vad_model": "",  # vad模型地址
    "funasr_device": "",

    # 语音合成配置
    # tts流式
    "tts_stream": False,
    # 如果使用了音频文件则不需要填写说话人
    # 说话人
    "speaker": "",
    # 说话人音频文件
    "speaker_audio": "",
    # 说话人音频文件内容
    "speaker_prompt": "",
    # cosyvoice模型
    "cosyvoice_model": "",
    # 抖音TTS
    "douyin_tts_host": "",
    "douyin_app_id": "",
    "douyin_token": "",
    "douyin_voice_type": "",  # 声音id
    "douyin_cluster": "",

}

default_config_file = "default_config.json"


def ensure_file_exists(filepath: str, default_content: Dict[str, Any]):
    """
    确保文件存在，如果不存在则创建并写入默认内容。

    :param filepath: 文件路径
    :param default_content: 默认内容
    """
    if not os.path.exists(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default_content, f, indent=4)
        logger.info(f"Created default configuration file at {filepath}.")


class Config(dict):
    def __init__(self, file_name: str = "config/config.json", encoding: str = "utf-8"):
        """
        初始化配置类。

        :param file_name: 主配置文件路径
        :param encoding: 文件编码
        """
        super().__init__()
        self.encoding = encoding
        self.file_name = file_name
        self.default_file = self.get_config_file_path(default_config_file)

        # 确保默认配置文件存在
        ensure_file_exists(self.default_file, available_setting)
        self.load_config(self.get_config_file_path(file_name))

    def load_config(self, filename: str):
        """
        加载JSON配置文件。

        :param filename: 配置文件路径
        """
        if not os.path.exists(filename):
            logger.warning(f"{filename} not found. Loading default configuration.")
            filename = self.default_file

        try:
            with open(filename, 'r', encoding=self.encoding) as f:
                config_data = json.load(f)
                for k, v in config_data.items():
                    self[k] = v
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file '{filename}' not found.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON file '{filename}': {e}")

    @staticmethod
    def get_config_file_path(file_name: str) -> str:
        """
        获取配置文件的完整路径。

        :param file_name: 配置文件名
        :return: 配置文件的完整路径
        """
        # 获取当前文件的目录路径（common 文件夹）
        common_dir = os.path.dirname(os.path.abspath(__file__))
        # 向上导航到项目根目录
        project_root = os.path.dirname(common_dir)
        # 构建到配置文件的完整路径
        return os.path.join(project_root, file_name)

    def __getitem__(self, key: str) -> Any:
        if key not in available_setting:
            raise KeyError(f"Key {key} not in available_setting")
        return super().get(key, available_setting[key])

    def __setitem__(self, key: str, value: Any):
        if key not in available_setting:
            raise KeyError(f"Key {key} not in available_setting")
        super().__setitem__(key, value)


config = Config()


def conf() -> Config:
    """获取全局配置实例"""
    return config


if __name__ == '__main__':
    if config["vad_path"]:
        print(config["vad_path"])
    else:
        print("vad_path not found")
