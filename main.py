# app.py (Flask backend for real-time AI PR review dashboard)
import os
import threading
from flask import Flask, render_template, request, Response
from dotenv import load_dotenv
from queue import Queue
from time import sleep

from interactive_langchain_reviewer import run_review_with_callback

load_dotenv()

app = Flask(__name__)
log_queue = Queue()

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

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

    threading.Thread(target=lambda: run_review_with_callback(repo, base, pr, log_queue)).start()
    return {"status": "started"}

if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
