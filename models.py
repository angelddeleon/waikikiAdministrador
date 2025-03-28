from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'ad'  # Especificamos el nombre de la tabla en la base de datos

    id_usuario = db.Column(db.Integer, primary_key=True)  # ID del usuario
    tipo_usuario = db.Column(db.String(50), nullable=False)  # Tipo de usuario (admin, empleado, etc.)
    correo_usuario = db.Column(db.String(120), unique=True, nullable=False)  # Correo del usuario
    nombre = db.Column(db.String(100), nullable=False)  # Nombre del usuario
    contrasena = db.Column(db.String(200), nullable=False)  # Contraseña del usuario (hasheada)

    def __repr__(self):
        return f"<User {self.nombre} {self.apellidos} - {self.correo_usuario}>"

    # Método para establecer una contraseña hasheada
    def set_password(self, password):
        self.contrasena = generate_password_hash(password)

    # Método para verificar la contraseña
    def check_password(self, password):
        return check_password_hash(self.contrasena, password)