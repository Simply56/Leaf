from flask import Flask, render_template, request, redirect, url_for
import sys
import json
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename
import qrcode

"""
This project specificaly avoids some new features because it is mean to be run on older versions of Python
"""

# TODO: Allow custom sorting on the home page (alphabetical, days since last watered, when was the plant added)

app = Flask(__name__)

# Ensure the data directory exists
if not os.path.exists("data"):
    os.makedirs("data")

# Ensure the plant images directory exists
PLANT_IMAGES_DIR = "static/plant_images"
if not os.path.exists(PLANT_IMAGES_DIR):
    os.makedirs(PLANT_IMAGES_DIR)

DATA_FILE = "data/plants.json"
DEFAULT_PLANT_IMAGE = "icon.png"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def delete_old_image(image_path):
    if image_path == DEFAULT_PLANT_IMAGE:
        return
    if image_path:
        full_path = os.path.join("static", image_path)
        if os.path.exists(full_path):
            os.remove(full_path)


def compute_watered_ago(plants):
    now = date.today()
    for id, plant in plants.items():
        if plant["last_watered"] is None:
            continue
        last_watered_date = datetime.strptime(
            plant["last_watered"], "%Y-%m-%d"
        ).date()
        watered_ago = (now - last_watered_date).days

        plant["watered_ago"] = watered_ago
    return plants


def load_plants():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            raw_load = dict()
            try:
                raw_load = json.load(f)
            except json.JSONDecodeError:
                return {}
            if raw_load is None:
                return {}

            return compute_watered_ago(raw_load)
    return {}


def save_plants(plants):
    with open(DATA_FILE, "w") as f:
        json.dump(plants, f)

def value_to_color(value: float, max_value: float = 10) -> str:
    ratio = min(value / max_value, 1)
    hue = int(120 - 120 * ratio)  # 120 = green, 0 = red
    return f"hsl({hue}, 100%, 40%)"
app.jinja_env.globals['value_to_color'] = value_to_color  # as a global function

@app.route("/")
def index():
    plants = load_plants()
    return render_template("index.j2", plants=plants)


@app.route("/add_plant", methods=["POST"])
def add_plant():
    plants = load_plants()
    plant_id = str(max(map(int, set(plants.keys()).union({0}))) + 1)
    plants[plant_id] = {
        "last_watered": None,
        "name": request.form.get("name", f"Plant {plant_id}"),
        "image_path": DEFAULT_PLANT_IMAGE,
    }
    save_plants(plants)
    return redirect(url_for("index"))


@app.route("/water/<plant_id>", methods=["POST"])
def water_plant(plant_id):
    plants = load_plants()
    if plant_id in plants:
        watering_time = request.form.get("watering_time")
        if watering_time:
            plants[plant_id]["last_watered"] = watering_time
        else:
            plants[plant_id]["last_watered"] = date.today().isoformat()
        save_plants(plants)
    return redirect(url_for("plant_status", plant_id=plant_id))


@app.route("/upload_image/<plant_id>", methods=["POST"])
def upload_image(plant_id):
    plants = load_plants()
    if plant_id in plants and "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            # Delete old image if it exists and isn't the default
            delete_old_image(plants[plant_id]["image_path"])

            # Save new image
            filename = secure_filename(f"plant_{plant_id}_{file.filename}")
            file_path = os.path.join(PLANT_IMAGES_DIR, filename)
            file.save(file_path)

            # Update plant data
            plants[plant_id]["image_path"] = os.path.join(
                "plant_images", filename
            )
            save_plants(plants)

    return redirect(url_for("plant_status", plant_id=plant_id))


@app.route("/plant/<plant_id>")
def plant_status(plant_id):
    plants = load_plants()
    plant = plants.get(plant_id, {})
    last_watered = None
    if plant.get("last_watered"):
        last_watered = datetime.strptime(
            plant["last_watered"], "%Y-%m-%d"
        ).date()
    today = date.today()
    return render_template(
        "plant.j2",
        plant_id=plant_id,
        plant=plant,
        last_watered=last_watered,
        now=today,
    )


@app.route("/delete/<plant_id>", methods=["POST"])
def delete_plant(plant_id):
    plants = load_plants()
    plant = plants.get(plant_id, {})

    # Delete the image
    delete_old_image(plant["image_path"])
    try:
        plants.pop(plant_id)
    except KeyError:
        pass

    save_plants(plants)
    return redirect(url_for("index"))


@app.route("/generate_qr_codes")
def generate_qr_codes():
    plants = load_plants()
    qr_codes = {}

    for plant_id, plant in plants.items():
        # Generate QR code
        plant_url = request.host_url.rstrip("/") + url_for(
            "plant_status", plant_id=plant_id
        )
        qr = qrcode.QRCode(version=1, box_size=1, border=1)
        qr.add_data(plant_url)
        qr.make(fit=True)

        # Get QR code as text
        qr_text  = qr.get_matrix()
        qr_codes[plant_id] = {"name": plant["name"], "qr": qr_text}

    return render_template("qr_codes.j2", qr_codes=qr_codes)


if __name__ == "__main__":
    # Example: python3 app.py debug
    if len(sys.argv) == 2 and sys.argv[1].lower() == "debug":
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        app.run(host="0.0.0.0", port=5000, debug=False)
