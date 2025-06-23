import logging
from PySide6.QtNetwork import QTcpSocket
from PySide6.QtCore import QObject, Signal, QByteArray, QTimer
from async_message import AsyncMessageHandler

# 配置日志输出格式与级别
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.DEBUG
)


class TcpClient(QObject):
    # 自定义信号
    connected = Signal()
    disconnected = Signal()
    error_occurred = Signal(str)
    raw_data_received = Signal(QTcpSocket, bytes)         # 原始数据
    async_raw_data_received = Signal(QTcpSocket, bytes)   # 异步处理结果

    def __init__(self, parent=None, host='127.0.0.1', port=12345, auto_reconnect=True, reconnect_interval=5000):
        super().__init__(parent)
        self.host: str = host
        self.port: int = port
        # TCP Socket 初始化
        self.socket = QTcpSocket()
        self.buffer = QByteArray()
        self.expected_size = None  # 预期接收的数据长度（从4字节头解析）

        # 自动重连设置
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.reconnect_timer = QTimer()
        self.reconnect_timer.setInterval(reconnect_interval)
        self.reconnect_timer.timeout.connect(self._attempt_reconnect)

        # 消息异步处理器
        self.handler = AsyncMessageHandler()
        self.handler.message_handled.connect(self._on_message_handled)
        self.raw_data_received.connect(self.handler.handle_message)

        # Socket 信号绑定
        self.socket.readyRead.connect(self._on_ready_read)
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.errorOccurred.connect(self._on_error)

        # 心跳发送定时器（每5秒）
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.setInterval(5000)
        self.heartbeat_timer.timeout.connect(self._send_heartbeat)

        # 心跳接收检测定时器（15秒内未收到数据则断线）
        self.last_received_time = QTimer()
        self.last_received_time.setInterval(15000)
        self.last_received_time.setSingleShot(True)
        self.last_received_time.timeout.connect(self._handle_heartbeat_timeout)

    def connect_to_server(self, host, port):
        """连接到指定 TCP 服务器"""
        if host:
            self.host = host
        if port:
            self.port = port
        try:
            self.socket.connectToHost(self.host, self.port)
          
        except Exception as e:
            pass

    def disconnect(self):
        """主动断开连接，并关闭定时器"""
        self.auto_reconnect = False
        try:
            if self.reconnect_timer.isActive():
                self.reconnect_timer.stop()
            self.socket.disconnectFromHost()
        except Exception as e:
            logging.error(f"Error during disconnect: {e}")

    def send_data(self, data: bytes):
        """向服务器发送数据，附带4字节长度前缀"""
        logging.info(f"Client sending data: {data}")
        if self.socket.state() == QTcpSocket.ConnectedState:
            try:
                length_prefix = len(data).to_bytes(4, 'big')
                self.socket.write(QByteArray(length_prefix + data))
            except Exception as e:
                logging.error(f"Send error: {e}")
        else:
            logging.warning("Send failed: socket not connected")

    def _on_ready_read(self):
        """处理接收到的数据流，提取完整的数据帧"""
        try:
            self.last_received_time.start()  # 每次有数据就重置超时计时器

            self.buffer.append(self.socket.readAll())

            while True:
                if self.expected_size is None:
                    if self.buffer.size() < 4:
                        break  # 不足4字节头，等下次接收
                    length_bytes = self.buffer.left(4)
                    self.expected_size = int.from_bytes(length_bytes.data(), 'big')
                    self.buffer.remove(0, 4)

                if self.buffer.size() < self.expected_size:
                    break  # 数据不足，继续等待

                data = self.buffer.left(self.expected_size)
                self.buffer.remove(0, self.expected_size)
                self.expected_size = None

                if data == b'__HEARTBEAT_ACK__':
                    return  # 心跳应答不再分发

                self.raw_data_received.emit(self.socket, bytes(data))
        except Exception as e:
            logging.error(f"Error in _on_ready_read: {e}")

    def _on_message_handled(self, socket, data: bytes):
        """异步消息处理完成后回调"""
        try:
            logging.info(f"[AsyncHandler] {data.decode(errors='ignore')}")
            self.async_raw_data_received.emit(socket, data)
        except Exception as e:
            logging.error(f"Error in _on_message_handled: {e}")

    def _on_connected(self):
        """成功建立连接后触发"""
        try:
            logging.info("Connected to server.")
            if self.reconnect_timer.isActive():
                self.reconnect_timer.stop()
            self.handler.start()
            self.connected.emit()
            self.heartbeat_timer.start()
            self.last_received_time.start()
        except Exception as e:
            logging.error(f"Error in _on_connected: {e}")

    def _on_disconnected(self):
        """连接断开后触发"""
        try:
            logging.warning("Disconnected from server.")
            self.heartbeat_timer.stop()
            self.last_received_time.stop()
            self.disconnected.emit()
            if self.auto_reconnect:
                self.reconnect_timer.start()
        except Exception as e:
            logging.error(f"Error in _on_disconnected: {e}")

    def _on_error(self, socket_error):
        """处理 socket 错误"""
        try:
            msg = f"Socket error: {socket_error}"
            logging.error(msg)
            self.error_occurred.emit(msg)
            if self.auto_reconnect:
                self.reconnect_timer.start()
        except Exception as e:
            logging.error(f"Error in _on_error: {e}")

    def _attempt_reconnect(self):
        """尝试重连服务器"""

        try:
            logging.info("Attempting reconnect...")
            self.connect_to_server(self.host, self.port)
        except Exception as e:
            logging.error(f"Error in _attempt_reconnect: {e}")

    def _send_heartbeat(self):
        """发送心跳包"""
        try:
            logging.debug("Sending heartbeat...")
            self.send_data(b'__HEARTBEAT__')
        except Exception as e:
            logging.error(f"Error in _send_heartbeat: {e}")

    def _handle_heartbeat_timeout(self):
        """心跳超时处理"""
        try:
            logging.warning("Heartbeat timeout. Forcing disconnect.")
            self.disconnect()
            self.reconnect_timer.start()
        except Exception as e:
            logging.error(f"Error in _handle_heartbeat_timeout: {e}")
