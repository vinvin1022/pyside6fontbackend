# test_client.py
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import QTimer
from tcp_server import TcpServer

import sys


class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TCP server")
        self.resize(300, 200)

        self.server = TcpServer()
        self.layout = QVBoxLayout(self)
        self.send_btn = QPushButton("服务端", self)
        self.layout.addWidget(self.send_btn)

        self.server.start('127.0.0.1', 10501)
        self.server.data_received.connect(self.on_server_receive)

    def on_server_receive(self, client, data):
        message = data
        # self.text_display.append(f"[Server] Received: {message}")
        # q = QTimer()
        # q.singleShot(1000, lambda: self.server.send_data(client, f"Echo: {message}".encode()))
        # self.server.send_data(client, f"Echo: {message}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
