from flask import Flask, render_template, redirect, url_for, request, flash, session, Blueprint, current_app
from models import db, User
from werkzeug.security import check_password_hash
import os
from werkzeug.utils import secure_filename
from flask import jsonify, flash

main_routes = Blueprint('main', __name__)

# Asegúrate de que el directorio de la carpeta exista
UPLOAD_FOLDER = 'static/imagenes/inmuebles'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main_routes.route('/')
def index():
    return render_template('index.html')


@main_routes.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))  # Redirige al login si no hay usuario en sesión
    
    user_id = session['user_id']
    user = User.query.get(user_id)  # Obtener el usuario desde la base de datos

    if user:
        return render_template('dashboard.html', user=user)  # Muestra el dashboard con la información del usuario
    else:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('main.login'))

