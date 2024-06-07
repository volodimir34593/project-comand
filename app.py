from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename
import imghdr

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

LOTS_FILE = 'lots.json'
USERS_FILE = 'users.json'
lots = []
users = {}

def save_lots():
    with open(LOTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(lots, f, ensure_ascii=False, default=str)

def load_lots():
    global lots
    if os.path.exists(LOTS_FILE):
        with open(LOTS_FILE, 'r', encoding='utf-8') as f:
            lots = json.load(f)
            for lot in lots:
                lot['created_at'] = datetime.fromisoformat(lot['created_at'])

def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False)

def load_users():
    global users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)

load_lots()
load_users()

@app.route('/')
def index():
    return render_template('index.html', lots=lots)

@app.route('/create_lot', methods=['GET', 'POST'])
def create_lot():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    if request.method == 'POST':
        lot_name = request.form['lot_name']
        lot_description = request.form['lot_description']
        lot_start_price = float(request.form['lot_start_price'])
        lot_image = request.files['lot_image']
        user_ip = request.remote_addr

        if lot_image and allowed_file(lot_image.filename) and is_image_file(lot_image.stream):
            filename = secure_filename(lot_image.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            lot_image.save(file_path)
            image_url = url_for('static', filename='uploads/' + filename)
        else:
            return render_template('create_lot.html', error='Потрібно завантажити зображення як файл')

        new_lot = {
            'name': lot_name,
            'description': lot_description,
            'start_price': lot_start_price,
            'created_at': datetime.now().isoformat(),
            'owner': session['username'],
            'image_url': image_url,
            'user_ip': user_ip
        }
        lots.append(new_lot)
        save_lots()
        return redirect(url_for('index'))
    return render_template('create_lot.html')

@app.route('/api/lots', methods=['GET', 'POST'])
def api_lots():
    if request.method == 'GET':
        return jsonify(lots)
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username not in users or users[username] != password:
            return jsonify({'error': 'Unauthorized'}), 401

        lot_name = request.form.get('lot_name')
        lot_description = request.form.get('lot_description')
        lot_start_price = float(request.form.get('lot_start_price', 0))
        lot_image = request.files.get('lot_image')

        if lot_image and allowed_file(lot_image.filename) and is_image_file(lot_image.stream):
            filename = secure_filename(lot_image.filename)
            lot_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"{request.host_url}static/uploads/{filename}"
        else:
            image_url = None

        new_lot = {
            'name': lot_name,
            'description': lot_description,
            'start_price': lot_start_price,
            'created_at': datetime.now().isoformat(),
            'owner': username,
            'image_url': image_url
        }
        lots.append(new_lot)
        save_lots()
        return jsonify(new_lot), 201

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Неправильне ім\'я користувача або пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template('register.html', error='Це ім\'я користувача вже зайняте')
        users[username] = password
        session['logged_in'] = True
        session['username'] = username
        save_users()
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/lot/<int:lot_id>/delete', methods=['POST'])
def delete_lot(lot_id):
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    lot = next((lot for lot in lots if lots.index(lot) == lot_id), None)
    if lot and lot['owner'] == session['username']:
        lots.pop(lot_id)
        save_lots()
        return redirect(url_for('index'))
    return redirect(url_for('index'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image_file(file_stream):
    header = file_stream.read(512)
    file_stream.seek(0)
    image_type = imghdr.what(None, header)
    return image_type is not None

if __name__ == '__main__':
    app.run(debug=True)
