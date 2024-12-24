import logging
import sys
import os


def setup_logger(log_level=logging.INFO):
    # 创建一个日志记录器
    log = logging.getLogger(__name__)
    log.setLevel(log_level)

    # 清除已存在的 handlers
    for handler in log.handlers[:]:
        log.removeHandler(handler)

    # 创建控制台日志处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    log.addHandler(console_handler)

    # 获取当前文件所在的目录，即 common 目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取 config 目录的路径，它是 common 目录的上级目录下的 config 目录
    config_dir = os.path.join(os.path.dirname(current_dir), 'config')

    # 确保config文件夹存在，如果不存在则创建
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # 创建文件日志处理器，保存在config文件夹中
    log_file = os.path.join(config_dir, "run.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(console_formatter)
    log.addHandler(file_handler)

    return log


# 配置并获取日志记录器
logger = setup_logger()
