import threading
from random import random

from flask import Flask, jsonify, send_from_directory
# from flask_cors import CORS

app = Flask(__name__, static_folder="dist")
# CORS(app)  # 允许跨域


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    print(f"path: {path}")
    return send_from_directory("web", path)

def xunhuan():
    while True:
        print(random())

@app.route("/api/hello")
def hello():
    threading.Thread(target=xunhuan, daemon=True).start()
    return jsonify({"message": "Hello from Flask!", "list": [
        {"id": 0, "name": 'Umi', "nickName": 'U', "gender": 'MALE'},
        {"id": 1, "name": 'Fish', "nickName": 'B', "gender": 'FEMALE'},
    ]})


# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=5000)
