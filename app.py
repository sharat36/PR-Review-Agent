# app.py (Flask backend for AI PR Reviewer + Chat UI)
import os
import threading
from flask import Flask, render_template, request, Response, send_from_directory, jsonify
from dotenv import load_dotenv
from queue import Queue
from time import sleep

from interactive_langchain_reviewer import run_review_with_callback, set_user_input

load_dotenv()

app = Flask(__name__)
log_queue = Queue()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/stream")
def stream():
    def event_stream():
        while True:
            msg = log_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/start", methods=["POST"])
def start():
    repo = request.form["repo"]
    base = request.form["base"]
    pr = request.form["pr"]

    threading.Thread(target=lambda: run_review_with_callback(repo, base, pr, log_queue.put)).start()
    return {"status": "started"}

@app.route("/chat_reply", methods=["POST"])
def chat_reply():
    data = request.get_json()
    if "message" in data:
        set_user_input(data["message"])
        return jsonify({"status": "received"})
    return jsonify({"error": "No message sent"}), 400

if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
