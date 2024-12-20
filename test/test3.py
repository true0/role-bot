import os
import time
import json
import winreg
import configparser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QSystemTrayIcon, QMenu, QAction, \
    qApp
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import sys


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def on_moved(self, event):
        if event.is_directory:
            return
        time.sleep(0.1)
        file_path = event.dest_path
        print(file_path)
        if file_path in processed_files and processed_files[file_path]:
            return
        os.chmod(file_path, 0o777)  # 解除新增文件的只读状态
        print('解除新增文件只读状态:', file_path)
        self.text_edit.append('解除新增文件只读状态:' + str(file_path))
        self.text_edit.setReadOnly(True)  # 设置文本框不可手动编辑
        # 保存已处理过的文件列表
        try:
            with open(json_path, 'w') as f:
                json.dump(processed_files, f)
        except Exception as e:
            window.text_edit.append("写入失败:" + str(e))


class App(QWidget):
    APP_PATH = os.path.abspath(sys.argv[0])
    DIR_PATH = os.path.dirname(APP_PATH)

    def __init__(self):
        super().__init__()
        self.text_edit = QTextEdit()  # 创建 text_edit 属性
        self.text_edit.setReadOnly(True)  # 设置文本框不可手动编辑
        self.initUI()
        self.tray = Tray(self)

    def initUI(self):
        self.setWindowTitle('微信监控并解除只读')
        self.setGeometry(100, 100, 700, 500)
        self.setWindowIcon(QIcon(DIR_PATH + '\ico.png'))

        # 创建垂直布局
        vbox = QVBoxLayout()

        # 创建文本框
        vbox.addWidget(self.text_edit)

        # 创建按钮
        self.button = QPushButton('设置开机自启')
        self.button.clicked.connect(self.toggle_startup)
        vbox.addWidget(self.button)

        # 创建清空按钮
        clear_button = QPushButton('清空文本框')
        clear_button.clicked.connect(self.clear_text_edit)
        vbox.addWidget(clear_button)

        # 设置布局
        self.setLayout(vbox)

        # 设置开机自启
        if config.getboolean('AUTO_STARTUP', 'enabled'):
            self.set_startup_enabled()
            self.button.setText('取消开机自启')
        else:
            self.set_startup_disabled()
            self.button.setText('设置开机自启')

    def toggle_startup(self):
        if config.getboolean('AUTO_STARTUP', 'enabled'):
            self.set_startup_disabled()
            config.set('AUTO_STARTUP', 'enabled', 'false')
            self.button.setText('设置开机自启')
            # self.text_edit.append('已取消开机自启')
        else:
            self.set_startup_enabled()
            config.set('AUTO_STARTUP', 'enabled', 'true')
            self.button.setText('取消开机自启')

        # 将修改后的配置写入配置文件
        with open(config_path, 'w') as f:
            config.write(f)

    def set_startup_enabled(self):

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0,
                             winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key, "ChatGPT", 0, winreg.REG_SZ, APP_PATH)
        winreg.CloseKey(key)
        self.text_edit.append('已设置开机自启')

    def set_startup_disabled(self):
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                winreg.DeleteValue(key, "ChatGPT")
                self.text_edit.append('已取消开机自启')
            except FileNotFoundError:
                self.text_edit.append('未设置开机自启，不需取消')

    def clear_text_edit(self):
        self.text_edit.clear()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.show()

    def showEvent(self, event):
        # 窗口显示时将焦点设置到文本框
        self.text_edit.setFocus()

    def mouseDoubleClickEvent(self, event):
        self.show()

    def show(self):
        super().show()


class Tray(QSystemTrayIcon):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setIcon(QIcon('ico.png'))
        self.setVisible(True)
        menu = QMenu()
        show_action = QAction('显示', self)
        show_action.triggered.connect(self.show_app)
        menu.addAction(show_action)

        exit_action = QAction('退出', self)
        exit_action.triggered.connect(qApp.quit)
        menu.addAction(exit_action)

        self.setContextMenu(menu)

    # def show_app(self):
    #   self.app.show()
    #   self.app.setWindowState(Qt.WindowActive)
    #   self.hide()

    def mouseDoubleClickEvent(self, event):
        if self.app.isHidden():
            self.app.show()
        else:
            self.app.hide()

    def show_app(self):
        self.app.show()
        self.app.setWindowState(Qt.WindowActive)
        # self.setToolTip('微信监控并解除只读\n双击隐藏')

    def hide_app(self):
        self.app.hide()
        # self.setToolTip('微信监控并解除只读\n双击显示')


if __name__ == '__main__':

    # 获取程序绝对路径
    # APP_PATH = os.path.abspath(__file__)
    APP_PATH = os.path.abspath(sys.argv[0])
    DIR_PATH = os.path.dirname(APP_PATH)
    # 读取配置文件
    config = configparser.ConfigParser()
    config_path = DIR_PATH + '\config.ini'
    config.read(config_path)

    app = QApplication([])

    window = App()
    # 获取用户文档路径
    documents_folder_key_path = r"Software\Tencent\WeChat"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, documents_folder_key_path) as key:
        user_documents_path, _ = winreg.QueryValueEx(key, "FileSavePath")

    if user_documents_path == "MyDocument:":
        documents_folder_key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, documents_folder_key_path) as key:
            user_documents_path, _ = winreg.QueryValueEx(key, "Personal")

    user_documents_path = user_documents_path + "\WeChat Files"
    window.text_edit.append("微信保存文件夹位置:" + user_documents_path)

    # 获取子文件夹下所有以 "wxid" 开头的文件夹中的 "FileStorage\File" 文件夹
    parent_folder = user_documents_path
    target_folders = []
    for dirpath, dirnames, filenames in os.walk(parent_folder):
        for dirname in dirnames:
            if dirname.startswith('wxid') or dirname.startswith('notsolo') or dirname.startswith('chu352150070'):
                target_folder = os.path.join(dirpath, dirname, 'FileStorage\File')
                if os.path.exists(target_folder):
                    target_folders.append(target_folder)
    window.text_edit.append("目标文件夹列表:" + str(target_folders))
    # 加载已处理过的文件列表
    processed_files = {}
    json_path = DIR_PATH + '\processed_files.json'
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            processed_files = json.load(f)

    # 解除目标文件夹及其子文件夹下所有文件的只读状态
    for target_folder in target_folders:
        for dirpath, dirnames, filenames in os.walk(target_folder):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if file_path in processed_files and processed_files[file_path]:
                    continue
                os.chmod(file_path, 0o777)  # 解除文件只读状态
                processed_files[file_path] = True  # 标记文件已处理
                window.text_edit.append("解除只读状态:" + str(file_path))

    # 保存已处理过的文件列表
    try:
        with open(json_path, 'w') as f:
            json.dump(processed_files, f)
    except Exception as e:
        window.text_edit.append("写入失败:" + str(e))

    # 监听目标文件夹及其子文件夹下新增文件，并解除只读状态
    window.text_edit.append("开始监听文件...")
    window.text_edit.setReadOnly(True)  # 设置文本框不可手动编辑
    processed_files = {}
    event_handler = FileEventHandler(window.text_edit)
    observer = Observer()
    for target_folder in target_folders:
        observer.schedule(event_handler, path=target_folder, recursive=True)
    observer.start()
    window.show()
    app.exec_()

    observer.stop()
    observer.join()
    qApp.quit()