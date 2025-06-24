import signal
import sys
import os
import threading
import time
from random import randint

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QStatusBar, QMenuBar
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebChannel import QWebChannel
from bridge import Bridge
import requests
from backend.server import kill_gunicorn, run_flask, start_gunicorn
# from PySide6.QtWidgets import QSplashScreen


def get_dist_path(filename: str) -> str:
    if getattr(sys, 'frozen', False):
        # 如果是 PyInstaller 打包后的运行环境
        base_path = sys._MEIPASS  # type: ignore
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, filename)


# def run_flask():
#     from backend.app import app
#
#     def _start():
#         # 可以加 debug=False 避免自动重启
#         app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
#
#     flask_thread = threading.Thread(target=_start, daemon=True)
#     flask_thread.start()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.timer = None
        self.setWindowTitle("PySide6 + React + Flask")
        self.resize(1024, 768)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.menu = QMenuBar()
        self.setMenuBar(self.menu)
        # self.menu.setNativeMenuBar(False)
        self.file_menu = self.menu.addMenu("File")
        self.send_action = QAction("Send Message", self)
        self.send_action.triggered.connect(self.send_message_to_frontend)
        self.file_menu.addAction(self.send_action)

        self.view = QWebEngineView()
        self.setCentralWidget(self.view)

        self.channel = QWebChannel()
        self.bridge = Bridge(self)
        self.channel.registerObject("pybridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        # 加载开发时的URL
        self.view.load(QUrl("http://localhost:5000"))

    def check_server(self):
        try:
            requests.get("http://127.0.0.1:5000", timeout=0.3)
            self.timer.stop()
            self.view.load(QUrl("http://127.0.0.1:5000"))
        except requests.exceptions.RequestException:
            pass  # 继续等待

    def send_message_to_frontend(self):
        num = randint(0,99999)
        self.view.page().runJavaScript("window.receiveFromPython(" + str(num) + ");")

    def update_status(self, text):
        self.status_bar.showMessage(text)

    def closeEvent(self, event):
        print("窗口正在关闭，清理 Gunicorn...")
        # self.clean_gunicorn()
        # kill_gunicorn(gunicorn_process)
        event.accept()


if __name__ == '__main__':
    # 启动 gunicorn
    # gunicorn_process = start_gunicorn()
    # 启动 Flask 线程
    threading.Thread(target=run_flask, daemon=True).start()

    # 启动 Qt 应用
    app = QApplication(sys.argv)

    # splash = QSplashScreen()
    # splash.show()

    window = MainWindow()

    # 定时检测 Flask 是否启动完成
    window.timer = QTimer()
    window.timer.timeout.connect(window.check_server)
    window.timer.start(100)  # 每 500ms 检查一次

    window.show()
    sys.exit(app.exec())

    # run_flask()
    #
    # # 等待服务器起来（简单等待2秒，也可以改为检测端口）
    # # 启动 gunicorn 在后台线程中运行
    # threading.Thread(target=run_gunicorn, daemon=True).start()

    # def cleanup():
    #     if gunicorn_process.poll() is None:
    #         os.killpg(os.getpgid(gunicorn_process.pid), signal.SIGTERM)
    #         gunicorn_process.wait()
    #         print("Gunicorn 清理完成")
    #
    #
    # app.aboutToQuit.connect(cleanup)
