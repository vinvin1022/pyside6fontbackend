# test_client.py
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton
from tcp_client import TcpClient
import sys


class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TCP Client Chat Example")
        self.resize(400, 300)

        self.client = TcpClient(auto_reconnect=True, reconnect_interval=2000)

        self.layout = QVBoxLayout(self)
        self.text_display = QTextEdit(self)
        self.text_input = QLineEdit(self)
        self.send_btn = QPushButton("Send", self)

        self.text_display.setReadOnly(True)
        self.layout.addWidget(self.text_display)
        self.layout.addWidget(self.text_input)
        self.layout.addWidget(self.send_btn)

        self.client.connect_to_server('127.0.0.1', 12345)

        self.send_btn.clicked.connect(self.send_message)

        self.client.raw_data_received.connect(self.on_client_receive)
        # self.client.async_raw_data_received.connect(self.on_client_receive)


    def send_message(self):
        text = self.text_input.text().strip()
        if text:
            self.client.send_data(text.encode())
            self.text_display.append(f"[我说]: {text}")
            self.text_input.clear()

    def on_client_receive(self, socket, data: bytes):
        print(f"client socket: {socket}")
        self.text_display.append(f"[他回复]: {data.decode()}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
