from flask import Flask
from config import Config
from routes import main_routes
from models import db  # Importa db desde el archivo de modelos
import os

app = Flask(__name__)
app.config.from_object(Config)

# Configuración para aceptar las imágenes
UPLOAD_FOLDER = 'static/imagenes/inmuebles'  
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inicializa la instancia de SQLAlchemy con la aplicación
db.init_app(app)

# Registrar las rutas desde otro archivo
app.register_blueprint(main_routes)

if __name__ == '__main__':
    app.run(debug=True)
