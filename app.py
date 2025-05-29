from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
from datetime import datetime
from dateutil.parser import parse
import os

app = Flask(__name__)

# Ensure the data directory exists
if not os.path.exists('data'):
    os.makedirs('data')

DATA_FILE = 'data/plants.json'

def load_plants():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_plants(plants):
    with open(DATA_FILE, 'w') as f:
        json.dump(plants, f)

@app.route('/')
def index():
    plants = load_plants()
    return render_template('index.html', plants=plants)

@app.route('/add_plant', methods=['POST'])
def add_plant():
    plants = load_plants()
    plant_id = str(len(plants) + 1)
    plants[plant_id] = {
        'last_watered': None,
        'name': request.form.get('name', f'Plant {plant_id}')
    }
    save_plants(plants)
    return redirect(url_for('index'))

@app.route('/water/<plant_id>', methods=['POST'])
def water_plant(plant_id):
    plants = load_plants()
    if plant_id in plants:
        plants[plant_id]['last_watered'] = datetime.now().isoformat()
        save_plants(plants)
    return redirect(url_for('plant_status', plant_id=plant_id))

@app.route('/plant/<plant_id>')
def plant_status(plant_id):
    plants = load_plants()
    plant = plants.get(plant_id, {})
    last_watered = None
    if plant.get('last_watered'):
        last_watered = parse(plant['last_watered'])
    now = datetime.now()
    return render_template('plant.html', 
                         plant_id=plant_id, 
                         plant=plant, 
                         last_watered=last_watered,
                         now=now)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False) 