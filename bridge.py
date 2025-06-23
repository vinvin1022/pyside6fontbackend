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
