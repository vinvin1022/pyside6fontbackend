import { useEffect, useState } from "react";

declare global {
  interface Window {
    pybridge: any;
    receiveFromPython: (msg: string) => void;
  }
}

export default function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    new (window as any).QWebChannel((window as any).qt.webChannelTransport, (channel: any) => {
      window.pybridge = channel.objects.pybridge;

      // 注册 PySide6 发来的调用
      window.receiveFromPython = (msg: string) => {
        console.log("收到来自 PySide6 的消息:", msg);
        setMessage(msg);
        // 可更新 UI
      };

      // 也可以立刻给 PySide6 发消息
      window.pybridge.receive_message("Hello from React!");
    });
  }, []);

  return (
    <div>
      <h1>React 与 PySide6 通信示例</h1>
      <p>PySide6 发来: {message}</p>
      <button onClick={() => window.pybridge.receive_message(Math.random().toString(36))}>
        向 PySide6 发消息
      </button>
    </div>
  );
}
