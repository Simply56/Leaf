from flask import Flask, render_template, request, redirect, url_for, send_file
import json
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename
import qrcode
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

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
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def delete_old_image(image_path):
    if image_path == DEFAULT_PLANT_IMAGE:
        return
    if image_path:
        full_path = os.path.join("static", image_path)
        if os.path.exists(full_path):
            os.remove(full_path)


def load_plants():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_plants(plants):
    with open(DATA_FILE, "w") as f:
        json.dump(plants, f)


@app.route("/")
def index():
    plants = load_plants()
    return render_template("index.html", plants=plants)


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
            plants[plant_id]["image_path"] = os.path.join("plant_images", filename)
            save_plants(plants)

    return redirect(url_for("plant_status", plant_id=plant_id))


@app.route("/plant/<plant_id>")
def plant_status(plant_id):
    plants = load_plants()
    plant = plants.get(plant_id, {})
    last_watered = None
    if plant.get("last_watered"):
        last_watered = datetime.strptime(plant["last_watered"], "%Y-%m-%d").date()
    today = date.today()
    return render_template(
        "plant.html",
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

    # Create a BytesIO buffer to store the PDF
    buffer = BytesIO()
    # Create the PDF object
    p = canvas.Canvas(buffer, pagesize=letter)

    # Set up grid parameters
    qr_size = 1.5 * inch
    margin = 0.5 * inch
    cols = 3
    rows = 4
    current_row = 0
    current_col = 0

    for plant_id, plant in plants.items():
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        plant_url = request.host_url.rstrip("/") + url_for(
            "plant_status", plant_id=plant_id
        )
        qr.add_data(plant_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Calculate position
        x = margin + (current_col * (qr_size + margin))
        y = letter[1] - margin - (current_row * (qr_size + margin)) - qr_size

        # Draw QR code directly using the PIL Image
        p.drawInlineImage(qr_img, x, y, width=qr_size, height=qr_size)

        # Draw plant name below QR code
        p.setFont("Helvetica", 10)
        p.drawString(x, y - 15, plant["name"])

        # Update position
        current_col += 1
        if current_col >= cols:
            current_col = 0
            current_row += 1
            if current_row >= rows:
                p.showPage()
                current_row = 0

    p.save()
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="plant_qr_codes.pdf",
    )


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
