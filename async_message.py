
# async_message.py
from PySide6.QtCore import QObject, Signal, QThread, QTimer


class AsyncMessageHandler(QObject):
    """
    通用异步消息处理器：运行在后台线程，用于处理来自 TcpServer 或 TcpClient 的消息。
    """
    message_handled = Signal(object, object)  # (source, data)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.queue = []  # 元素为 (source, data)
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self._process_queue)
        self.thread.started.connect(self.timer.start)

    def start(self):
        self.thread.start()

    def stop(self):
        self.timer.stop()
        self.thread.quit()
        self.thread.wait()

    def handle_message(self, source, data):
        self.queue.append((source, data))

    def _process_queue(self):
        while self.queue:
            source, data = self.queue.pop(0)
            # 实际处理逻辑可自定义
            # print(f"[AsyncHandler] {source} -> {data}")
            self.message_handled.emit(source, data)