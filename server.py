from flask import Flask, request, jsonify, session, abort,send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os, hashlib

import cloudinary
import cloudinary.uploader


app=Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecret')
# enable CORS for all resources
# CORS(app)
CORS(app, supports_credentials=True)
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
#-----------------------mail configuration--------------------
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']=587
app.config['MAIL_USE_TLS']=True
# app.config['MAIL_USERNAME']='awahidul606@gmail.com'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
# app.config['MAIL_PASSWORD']='icof mxko tcfy rrap'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER']='wahidul.b@decodeage.com'

mail=Mail(app)


# -----------------------Postgress database configuration--------------------
# app.config['SQLALCHEMY_DATABASE_URI'] ='postgresql://postgres:Wahidul123@localhost/interior_design'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# User model (simple admin)
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
# ----------------- Project Model -------------------
class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    project_name = db.Column(db.String(255))
    area = db.Column(db.String(255))
    type = db.Column(db.String(100))
    brief = db.Column(db.Text)
    solution = db.Column(db.Text)
    feedback = db.Column(db.Text)
    images = db.Column(db.JSON)
class GalleryImage(db.Model):
    __tablename__ = 'gallery_images'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    image_urls = db.Column(db.JSON)  # or db.JSONB if using PostgreSQL's JSONB
    uploaded_at = db.Column(db.DateTime, server_default=db.func.now())

# Hash helper
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()



# Login
@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    user = Admin.query.filter_by(username=data['username']).first()
    if user and user.password_hash == hash_password(data['password']):
        session['admin_id'] = user.id
        return jsonify({'message': 'Logged in'}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_id', None)
    return jsonify({'message': 'Logged out'}), 200

def admin_required(fn):
    def wrapper(*args, **kwargs):
        if 'admin_id' not in session:
            abort(401)
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper
# ----------------- Email Routes -------------------
@app.route('/send_email',methods=['POST'])
def send_email():
    data= request.get_json()

    name=data['name']
    email=data['email']
    message=data['message']

    # create the email message
    msg=Message(f"Message from {name}",recipients=['awahidul606@gmail.com'])
    msg.body=f"You have recieved a new mesage from {name} ({email}):\n\n{message}"
    try:
        mail.send(msg)
        print("Showed the successfull msg")
        return jsonify({'message':'Email sent successfully!'}),200
    except Exception as e:
        print("some error occuring",str(e))
        return jsonify({"error":str(e)}),500

@app.route('/service_mail',methods=['POST'])
def service_mail():
    data=request.get_json()
    name=data['name']
    mobile=data['mobile']
    property_type=data['propertyType']
    updates_via_whatsapp=data['updatesViaWhatsApp']
    msg=Message(subject="New consultation booking",
                sender='vellegngrameshwaram@gmail.com',
                recipients=['awahidul606@gmail.com']
                )
    msg.body=f"""
    Consultation Details:
    Name:{name},
    Mobile:{mobile},
    property type:{property_type},
    Updates Via WhatsApp:{'Yes' if updates_via_whatsapp else 'No'}
    """
    try:
         mail.send(msg)
         return jsonify({"message":"Email send successfully"}), 200
    except Exception as e:
         return jsonify({"error":str(e)}),500

# ----------------- Project Routes -------------------
@app.route('/projects', methods=['GET'])
def get_projects():
    projects = Project.query.all()
    result = []
    for p in projects:
        result.append({
            'id': p.id,
            'title': p.title,
            'project_name': p.project_name,
            'area': p.area,
            'type': p.type,
            'brief': p.brief,
            'solution': p.solution,
            'feedback': p.feedback,
            'images': p.images or []
        })
    return jsonify(result)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    # file.save(path)
    upload_result = cloudinary.uploader.upload(file)
    image_url = upload_result['secure_url']

    return jsonify({'url': image_url})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Add project route (admin-only)
@app.route('/admin/add_project', methods=['POST'])
@admin_required
def admin_add_project():
    data = request.get_json()

    # Ensure 'images' is a list of URLs (already handled in frontend after upload)
    image_urls = data.get('images', [])
    if not isinstance(image_urls, list):
        return jsonify({"error": "Images should be a list of URLs"}), 400

    project = Project(
        title=data['title'],
        project_name=data.get('project_name'),
        area=data.get('area'),
        type=data.get('type'),
        brief=data.get('brief'),
        solution=data.get('solution'),
        feedback=data.get('feedback'),
        images=image_urls  # Stored as a JSON array
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({'message': 'Project added successfully'}), 201


# Add gallery photos 
@app.route('/api/gallery/upload', methods=['POST'])
def upload_gallery_images():
    if 'images' not in request.files:
        return jsonify({'error': 'No image files uploaded'}), 400

    uploaded_files = request.files.getlist('images')
    title = request.form.get('title', 'Untitled')
    image_urls = []

    for file in uploaded_files:
        if file.filename == '':
            continue
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        image_url = f'http://localhost:5000/uploads/{filename}'
        image_urls.append(image_url)

    # Save to gallery_images table
    gallery_entry = GalleryImage(
        title=title,
        image_urls=image_urls
    )
    db.session.add(gallery_entry)
    db.session.commit()

    return jsonify({'message': '✅ Images uploaded successfully!', 'images': image_urls}), 201
@app.route('/api/gallery', methods=['GET'])
def get_gallery_images():
    entries = GalleryImage.query.order_by(GalleryImage.uploaded_at.desc()).all()
    
    # Flatten all image URLs into one list
    all_images = []
    for entry in entries:
        all_images.extend(entry.image_urls or [])
    print(all_images)
    return jsonify(all_images)

# ----------------- DB Init (Once) -------------------
def init_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            db.session.add(Admin(username='admin', password_hash=hash_password('admin123')))
            db.session.commit()
            
@app.route('/init_db')
def trigger_init_db():
    init_db()
    return "✅ Database initialized on Render!"
if __name__=="__main__":
        init_db()
        app.run(debug=True)