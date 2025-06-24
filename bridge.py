from PySide6.QtCore import QObject, Slot


class Bridge(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    @Slot(str)
    def say_hello(self, message):
        self.main_window.update_status(message)

    @Slot(str)
    def from_js(self, message):
        self.main_window.update_status(message)

    @Slot(str)
    def receive_message(self, msg):
        print(f"React 发来的消息: {msg}")
        self.main_window.update_status(f"React 啊说: {msg}")