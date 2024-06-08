from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename
import imghdr
import uuid

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
                if 'id' not in lot:
                    lot['id'] = str(uuid.uuid4())

def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False)

def load_users():
    global users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image_file(file_stream):
    header = file_stream.read(512)
    file_stream.seek(0)
    image_type = imghdr.what(None, header)
    return image_type is not None

def find_lot_by_id(lot_id):
    for lot in lots:
        if str(lot['id']) == str(lot_id):
            return lot
    return None

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
        lot_images = request.files.getlist('lot_images[]')
        user_ip = request.remote_addr

        image_urls = []

        for lot_image in lot_images:
            if lot_image and allowed_file(lot_image.filename) and is_image_file(lot_image.stream):
                filename = secure_filename(lot_image.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                lot_image.save(file_path)
                image_url = url_for('static', filename='uploads/' + filename)
                image_urls.append(image_url)
            else:
                return render_template('create_lot.html', error='Потрібно завантажити зображення як файл')

        new_lot = {
            'id': str(uuid.uuid4()),
            'name': lot_name,
            'description': lot_description,
            'start_price': lot_start_price,
            'created_at': datetime.now().isoformat(),
            'owner': session['username'],
            'image_urls': image_urls,
            'user_ip': user_ip
        }
        lots.append(new_lot)
        save_lots()
        return redirect(url_for('index'))
    return render_template('create_lot.html')

@app.route('/edit_lot/<uuid:item_id>', methods=['GET', 'POST'])
def edit_lot(item_id):
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    lot = find_lot_by_id(item_id)
    if not lot:
        return "Лот не знайдено", 404

    if request.method == 'POST':
        if 'delete_images' in request.form:
            lot['image_urls'] = []  # Очищуємо список image_urls
            save_lots()
            return redirect(url_for('edit_lot', item_id=item_id))
        
        # Перевіряємо, чи було завантажено нові фото
        lot_images = request.files.getlist('lot_images[]')
        if lot_images:
            image_urls = lot['image_urls']  # Зберігаємо старі фото
            for lot_image in lot_images:
                if lot_image and allowed_file(lot_image.filename) and is_image_file(lot_image.stream):
                    filename = secure_filename(lot_image.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    lot_image.save(file_path)
                    image_url = url_for('static', filename='uploads/' + filename)
                    image_urls.append(image_url)
                else:
                    return render_template('edit_lot.html', lot=lot, error='Потрібно завантажити зображення як файл')
            lot['image_urls'] = image_urls

        # Оновлюємо дані лота
        lot_name = request.form['lot_name']
        lot_description = request.form['lot_description']
        lot_start_price = float(request.form['lot_start_price'])
        lot['name'] = lot_name
        lot['description'] = lot_description
        lot['start_price'] = lot_start_price

        # Зберігаємо оновлені дані
        save_lots()

        return redirect(url_for('item_page', item_id=item_id))

    return render_template('edit_lot.html', lot=lot)

@app.route('/item/<uuid:item_id>')
def item_page(item_id):
    lot = find_lot_by_id(item_id)
    if lot:
        return render_template('lots.html', lots=[lot])
    else:
        return "Товар не знайдено", 404


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
        lot_images = request.files.getlist('lot_images[]')

        image_urls = []

        for lot_image in lot_images:
            if lot_image and allowed_file(lot_image.filename) and is_image_file(lot_image.stream):
                filename = secure_filename(lot_image.filename)
                lot_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f"{request.host_url}static/uploads/{filename}"
                image_urls.append(image_url)
            else:
                return jsonify({'error': 'Потрібно завантажити зображення як файл'}), 400

        new_lot = {
            'id': str(uuid.uuid4()),
            'name': lot_name,
            'description': lot_description,
            'start_price': lot_start_price,
            'created_at': datetime.now().isoformat(),
            'owner': username,
            'image_urls': image_urls
        }
        lots.append(new_lot)
        save_lots()
        return jsonify(new_lot), 201
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = next((u for u in users.values() if u['email'] == email), None)
        if user and user['password'] == password:
            session['logged_in'] = True
            session['username'] = next(username for username, details in users.items() if details['email'] == email)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Неправильний email або пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        last_name = request.form['last_name']
        first_name = request.form['first_name']
        country_code = request.form['country_code']
        phone_number = request.form['phone_number']
        email = request.form['email']

        if password != password_confirm:
            return render_template('register.html', error='Паролі не співпадають')

        if any(user['email'] == email for user in users.values()):
            return render_template('register.html', error='Цей email вже зареєстрований')

        if username in users:
            return render_template('register.html', error='Це ім\'я користувача вже зайняте')

        full_phone_number = f"{country_code}{phone_number}"

        users[username] = {
            'password': password,
            'last_name': last_name,
            'first_name': first_name,
            'phone_number': full_phone_number,
            'email': email,
        }
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

@app.route('/delete_lot/<item_id>', methods=['POST'])
def delete_lot(item_id):
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    lot = find_lot_by_id(item_id)
    if lot and lot['owner'] == session['username']:
        lots.remove(lot)
        save_lots()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
