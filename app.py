import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO
from sqlalchemy import JSON

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'restaurant.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ---------- Models ----------
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    items = db.relationship('Item', backref='category', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Float, nullable=False)
    photo = db.Column(db.String(300), nullable=True)
    out_of_stock = db.Column(db.Boolean, default=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    variations = db.Column(JSON, default={})  # sizes, toppings

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    items = db.Column(JSON, nullable=False)  # list of {id, name, qty, size, price}
    total = db.Column(db.Float, nullable=False)
    car_info = db.Column(db.String(300))
    status = db.Column(db.String(50), default='pending')  # pending, accepted, ready, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------- Helpers ----------
def item_to_dict(item: Item):
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "photo": url_for('static', filename=f'uploads/{item.photo}') if item.photo else None,
        "out_of_stock": item.out_of_stock,
        "category": item.category.name if item.category else None,
        "variations": item.variations or {}
    }

def order_to_dict(o: Order):
    return {
        "id": o.id,
        "items": o.items,
        "total": o.total,
        "car_info": o.car_info,
        "status": o.status,
        "created_at": o.created_at.isoformat()
    }

# ---------- API Routes ----------
@app.route('/api/menu')
def api_menu():
    cats = Category.query.order_by(Category.name).all()
    data = []
    for c in cats:
        data.append({
            "id": c.id,
            "name": c.name,
            "items": [item_to_dict(i) for i in c.items]
        })
    return jsonify({"categories": data})

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"results": []})
    items = Item.query.filter(
        Item.name.ilike(f"%{q}%") | Item.description.ilike(f"%{q}%")
    ).all()
    return jsonify({"results": [item_to_dict(i) for i in items]})

@app.route('/api/order', methods=['POST'])
def api_order():
    data = request.json
    items = data.get('items', [])
    car_info = data.get('car_info', '')
    if not items:
        return jsonify({"error": "No items"}), 400
    total = sum(i.get('price', 0) * i.get('qty', 1) for i in items)
    order = Order(items=items, total=total, car_info=car_info, status='pending')
    db.session.add(order)
    db.session.commit()
    # notify admin clients
    socketio.emit('new_order', {"order_id": order.id, "order": order_to_dict(order)}, namespace='/admin')
    return jsonify({"order_id": order.id, "status": order.status})

@app.route('/api/order/<int:order_id>', methods=['GET'])
def api_get_order(order_id):
    o = Order.query.get_or_404(order_id)
    return jsonify(order_to_dict(o))

@app.route('/api/admin/orders')
def api_admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify([order_to_dict(o) for o in orders])

@app.route('/api/admin/order/<int:order_id>/update', methods=['POST'])
def api_admin_update_order(order_id):
    o = Order.query.get_or_404(order_id)
    new_status = request.json.get('status')
    if new_status:
        o.status = new_status
        db.session.commit()
        socketio.emit('order_update', {"order_id": o.id, "status": o.status}, namespace='/')
        return jsonify({"ok": True, "status": o.status})
    return jsonify({"error": "no status provided"}), 400

@app.route('/api/admin/item', methods=['POST'])
def api_admin_create_item():
    name = request.form.get('name')
    description = request.form.get('description', '')
    price = float(request.form.get('price', '0') or 0)
    category_name = request.form.get('category')
    out_of_stock = request.form.get('out_of_stock', 'false').lower() == 'true'
    variations = request.form.get('variations', '{}')
    try:
        variations = json.loads(variations)
    except:
        variations = {}
    photo_filename = None
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_filename = filename
    cat = Category.query.filter_by(name=category_name).first()
    if not cat:
        cat = Category(name=category_name)
        db.session.add(cat)
        db.session.commit()
    item = Item(name=name, description=description, price=price,
                photo=photo_filename, out_of_stock=out_of_stock,
                category=cat, variations=variations)
    db.session.add(item)
    db.session.commit()
    return jsonify({"ok": True, "item": item_to_dict(item)})

@app.route('/api/admin/item/<int:item_id>', methods=['POST'])
def api_admin_update_item(item_id):
    item = Item.query.get_or_404(item_id)
    payload = request.form
    item.name = payload.get('name', item.name)
    item.description = payload.get('description', item.description)
    item.price = float(payload.get('price', item.price) or item.price)
    item.out_of_stock = payload.get('out_of_stock', str(item.out_of_stock)).lower() == 'true'
    variations = payload.get('variations')
    if variations:
        try:
            item.variations = json.loads(variations)
        except:
            pass
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            item.photo = filename
    db.session.commit()
    return jsonify({"ok": True, "item": item_to_dict(item)})

@app.route('/api/admin/items')
def api_admin_items():
    items = Item.query.all()
    return jsonify([item_to_dict(i) for i in items])

# ---------- Pages ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/order-status/<int:order_id>')
def order_status_page(order_id):
    # Always serve React frontend
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    return render_template('admin.html')

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password','')
        if password == os.environ.get('ADMIN_PASSWORD','admin123'):
            session['is_admin'] = True
            return redirect(url_for('admin_page'))
        return "Invalid", 401
    return """
    <form method="post">
      <input name="password" placeholder="admin password"/>
      <button type="submit">Login</button>
    </form>
    """

# ---------- SocketIO ----------
@socketio.on('connect', namespace='/')
def ws_connect():
    pass

@socketio.on('connect', namespace='/admin')
def ws_admin_connect():
    pass

# ---------- Init ----------
def ensure_dirs():
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if __name__ == '__main__':
    ensure_dirs()

    with app.app_context():
        db.create_all()
        try:
            from seed import seed_database
            seed_database(db, Category, Item)
        except Exception as e:
            print("Seed skipped or failed:", e)
    socketio.run(app, host='0.0.0.0', port=5000)
