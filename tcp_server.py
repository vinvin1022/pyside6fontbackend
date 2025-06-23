import json
import struct
import time
import logging
from dataclasses import dataclass

from PySide6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket
from PySide6.QtCore import QObject, Signal, QByteArray
from enum import Enum, auto
from typing import Dict, Any, Optional
from async_message import AsyncMessageHandler

logging.getLogger().setLevel(logging.DEBUG)

class MessageType(Enum):
    """消息类型枚举"""
    # 系统消息
    HANDSHAKE = auto()  # 握手
    HEARTBEAT = auto()  # 心跳
    DISCONNECT = auto()  # 断开连接

    # 数据消息
    DATA_REQUEST = auto()  # 数据请求
    DATA_RESPONSE = auto()  # 数据响应

    # 控制消息
    COMMAND = auto()  # 命令
    COMMAND_ACK = auto()  # 命令确认

    # 状态消息
    STATUS_UPDATE = auto()  # 状态更新
    ERROR = auto()  # 错误


@dataclass
class MessageHeader:
    """消息头"""

    msg_type: MessageType  # 消息类型
    sequence: int  # 序列号
    timestamp: int  # 时间戳
    magic: bytes = b'PSQT'  # 魔数，用于标识协议
    version: int = 1  # 协议版本
    payload_size: int = 0  # 负载大小


class SocketMessage:
    """Socket消息封装类"""

    def __init__(self, msg_type: MessageType, sequence: int, payload: Dict[str, Any] = None):
        """
        初始化消息

        Args:
            msg_type: 消息类型
            sequence: 序列号
            payload: 消息负载，字典格式
        """
        self.header = MessageHeader(
            msg_type=msg_type,
            sequence=sequence,
            timestamp=int(time.time())
        )
        self.payload = payload if payload is not None else {}

    def pack(self) -> bytes:
        """
        将消息打包为二进制数据

        Returns:
            打包后的字节数据
        """
        # 将负载转换为JSON字符串，然后编码为UTF-8字节
        payload_bytes = json.dumps(self.payload).encode('utf-8')
        self.header.payload_size = len(payload_bytes)

        # 打包消息头
        header_bytes = struct.pack(
            '!4sHHIII',
            self.header.magic,  # 4字节魔数
            self.header.version,  # 2字节版本号
            self.header.msg_type.value,  # 2字节消息类型
            self.header.sequence,  # 4字节序列号
            self.header.timestamp,  # 4字节时间戳

            self.header.payload_size,  # 4字节负载大小
        )

        # 组合消息头和负载
        return header_bytes + payload_bytes

    @classmethod
    def unpack(cls, data: bytes) -> Optional['SocketMessage']:
        """
        解析二进制数据为消息对象

        Args:
            data: 接收到的二进制数据

        Returns:
            解析后的消息对象，解析失败则返回None
        """
        try:
            # 解析消息头
            header_size = struct.calcsize('!4sHHIII')
            data = bytes(data)
            if len(data) < header_size:
                return None

            magic, version, msg_type_value, sequence, timestamp, payload_size = struct.unpack(
                '!4sHHIII', data[:header_size]
            )
            # 验证魔数
            if magic != b'PSQT':
                return None

            # 解析消息负载
            payload_bytes = data[header_size:header_size + payload_size]
            if len(payload_bytes) != payload_size:
                return None

            payload = json.loads(payload_bytes.decode('utf-8'))

            # 创建消息对象
            msg = cls(MessageType(msg_type_value), sequence, payload)
            msg.header.timestamp = timestamp
            return msg

        except Exception as e:
            print(f"消息解析错误: {e}")
            return None

class TcpServer(QObject):
    # 定义信号
    client_connected = Signal(QTcpSocket)
    client_disconnected = Signal(QTcpSocket)
    data_received = Signal(QTcpSocket, object)            # 原始数据帧
    async_data_received = Signal(QTcpSocket, object)      # 异步处理结果

    def __init__(self, parent=None):
        super().__init__(parent)

        # TCP 服务器实例
        self.server = QTcpServer()
        self.server.newConnection.connect(self._on_new_connection)

        # 客户端管理
        self.clients = []
        self.buffers = {}          # 每个 client 的接收缓存
        self.expected_sizes = {}   # 每个 client 当前预期数据长度

        # 异步消息处理器
        self.handler = AsyncMessageHandler()
        self.handler.message_handled.connect(self._on_async_message_handled)
        self.handler.start()

    def start(self, host='127.0.0.1', port=12345) -> bool:
        """启动服务器监听"""
        if self.server.listen(QHostAddress(host), port):
            logging.info(f"Server listening on {host}:{port}")
            return True
        else:
            logging.error(f"Failed to start server: {self.server.errorString()}")
            return False

    def _on_new_connection(self):
        """处理新连接"""
        while self.server.hasPendingConnections():
            try:
                client = self.server.nextPendingConnection()

                # 绑定读写/断开信号
                client.readyRead.connect(lambda c=client: self._on_ready_read(c))
                client.disconnected.connect(lambda c=client: self._on_disconnected(c))

                self.clients.append(client)
                self.buffers[client] = QByteArray()
                self.expected_sizes[client] = None

                self.client_connected.emit(client)
                logging.info(f"New client connected: {client.peerAddress().toString()}:{client.peerPort()}")
            except Exception as e:
                logging.error(f"Error accepting new connection: {e}")

    def _on_ready_read(self, client: QTcpSocket):
        try:
            buffer = self.buffers.get(client)
            if buffer is None:
                logging.warning("Unknown client in readyRead")
                return

            buffer.append(client.readAll())

            # 处理所有可完整解析的消息
            while True:
                header_size = struct.calcsize('!4sHHIII')
                if buffer.size() < header_size:
                    break  # 等待更多数据

                # 先尝试读取 header
                header_bytes = buffer.left(header_size)
                try:
                    magic, version, msg_type_value, sequence, timestamp, payload_size = struct.unpack(
                        '!4sHHIII', bytes(header_bytes)
                    )
                except Exception as e:
                    logging.error(f"Header unpack failed: {e}")
                    break

                # 检查是否收到了完整 payload
                total_size = header_size + payload_size
                if buffer.size() < total_size:
                    break  # 数据还不完整，等下次继续

                # 拿到完整一帧，解析消息
                message_bytes = buffer.left(total_size)
                buffer.remove(0, total_size)

                unpacked_msg = SocketMessage.unpack(message_bytes)
                if not unpacked_msg:
                    logging.warning("Failed to unpack message")
                    continue

                logging.info(f"unpacked_msg.payload: {unpacked_msg.payload}")

                # 心跳处理
                if unpacked_msg.payload == '__HEARTBEAT__':
                    logging.debug(f"Heartbeat from {client.peerAddress().toString()}")
                    self.send_data(client, '__HEARTBEAT_ACK__')
                    continue

                self.data_received.emit(client, unpacked_msg.payload)
                self.handler.handle_message(client, unpacked_msg.payload)

        except Exception as e:
            logging.error(f"Error reading from client: {e}")

    def _on_disconnected(self, client: QTcpSocket):
        """客户端断开连接处理"""
        try:
            logging.info(f"Client disconnected: {client.peerAddress().toString()}:{client.peerPort()}")
            if client in self.clients:
                self.clients.remove(client)
                self.client_disconnected.emit(client)

            # 清理资源
            self.buffers.pop(client, None)
            self.expected_sizes.pop(client, None)
            client.deleteLater()

        except Exception as e:
            logging.error(f"Error during disconnection cleanup: {e}")

    def _on_async_message_handled(self, client: QTcpSocket, data: bytes):
        """异步处理器结果回调"""
        try:
            # logging.debug(f"[AsyncHandler] {data}")
            self.async_data_received.emit(client, data)
        except Exception as e:
            logging.error(f"Error in async result handling: {e}")

    def send_data(self, client: QTcpSocket, data):
        """向指定客户端发送数据，附加4字节长度头"""
        if client in self.clients and client.state() == QTcpSocket.ConnectedState:
            try:
                # length_prefix = len(data).to_bytes(4, 'big')
                # client.write(QByteArray(length_prefix + data))
                messages = SocketMessage(
                    msg_type=MessageType.STATUS_UPDATE,
                    sequence=42,
                    payload=data
                )

                d = messages.pack()
                logging.info(f"Client sending data: {d} to {client.peerAddress().toString()}:{client.peerPort()}")
                client.write(d)
                # logging.debug(f"Sent {len(data)} bytes to {client.peerAddress().toString()}:{client.peerPort()}")
            except Exception as e:
                logging.error(f"Send error: {e}")
        else:
            logging.warning("Send failed: client not connected or invalid.")
