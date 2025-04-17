from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
import threading
import queue
import time

from interactive_langchain_reviewer import run_review_with_callback, set_user_input

app = Flask(__name__)
CORS(app)

# Queue to stream logs to frontend via /stream
log_queue = queue.Queue()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start():
    repo = request.form.get("repo")
    base = request.form.get("base")
    pr = request.form.get("pr")

    def run():
        run_review_with_callback(repo, base, pr, lambda msg: log_queue.put(msg))

    threading.Thread(target=run).start()
    return jsonify({"status": "started"})


@app.route("/chat_reply", methods=["POST"])
def chat_reply():
    reply = request.form.get("reply", "").strip()
    set_user_input(reply)
    return jsonify({"status": "received"})


@app.route("/stream")
def stream():
    def event_stream():
        while True:
            try:
                message = log_queue.get(timeout=60)
                yield f"data: {message}\n\n"
            except queue.Empty:
                yield f"data: \n\n"

    return Response(event_stream(), content_type="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
