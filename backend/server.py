import subprocess
import os
import signal
from waitress import serve
from backend.app import app

def start_gunicorn():
    # 注意：一定要使用绝对路径导入 app
    os.chdir(os.path.dirname(__file__))

    gunicorn_cmd = [
        "gunicorn",
        "-w", "1",
        "-k", "gevent",
        "-b", "127.0.0.1:5000",
        "app:app"
    ]
    return subprocess.Popen(gunicorn_cmd, start_new_session=True)


def kill_gunicorn(proc: subprocess.Popen):
    if proc.poll() is None:
        try:
            if os.name == 'nt':
                # Windows 平台
                proc.terminate()
            else:
                # macOS / Linux：向进程组发送 SIGTERM
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait()
        except Exception as e:
            print("Failed to kill gunicorn:", e)


def run_flask():
    serve(app, host='0.0.0.0', port=5000)