from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from config import Config
from routes import main_routes
from models import db, Pago  # Importa db desde el archivo de modelos
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

@app.route('/update_payment_status', methods=['POST'])
def update_payment_status():
    try:
        payment_id = request.form['id']  # Obtener el ID del pago
        status = request.form['status']  # Obtener el nuevo estado

        # Buscar el pago en la base de datos
        pago = Pago.query.get(payment_id)

        if not pago:
            return jsonify({"error": "Pago no encontrado"}), 404

        # Actualizar el estado del pago
        pago.payment_status = status
        db.session.commit()  # Guardar los cambios en la base de datos

        return jsonify({"success": "Estado del pago actualizado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
