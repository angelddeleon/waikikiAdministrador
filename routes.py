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
        return render_template('dashboard.html')

@main_routes.route('/plantilla-datatable')
def plantilla():
        return render_template('plantilla-datatable.html')