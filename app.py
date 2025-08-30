from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from pathlib import Path
from generator import generate_infographic

app = Flask(__name__, static_folder="static", template_folder="sitetemplates")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    form = {k: request.form.get(k, "") for k in request.form.keys()}
    fname = generate_infographic(form)
    return redirect(url_for("serve_output", filename=fname))

@app.route("/outputs/<path:filename>")
def serve_output(filename):
    outputs = Path(app.static_folder) / "outputs"
    return send_from_directory(outputs, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
