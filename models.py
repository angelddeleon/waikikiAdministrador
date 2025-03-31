from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Numeric  # Importar Numeric de SQLAlchemy

db = SQLAlchemy()

# Modelo para la tabla 'usuarios'
class Usuario(db.Model):
    __tablename__ = 'usuarios'  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True)  # ID del usuario
    nombre = db.Column(db.String(255), nullable=False)  # Nombre del usuario
    email = db.Column(db.String(255), unique=True, nullable=False)  # Correo del usuario
    telefono = db.Column(db.String(15))  # Teléfono del usuario
    password = db.Column(db.String(255), nullable=False)  # Contraseña del usuario (hasheada)
    codigoPais = db.Column(db.String(10))  # Código de país
    role = db.Column(db.Enum('usuario', 'admin'), nullable=False)  # Rol del usuario
    isBlocked = db.Column(db.Boolean, default=False)  # Si el usuario está bloqueado
    perfil = db.Column(db.String(255))  # Perfil del usuario (foto, etc.)

    def __repr__(self):
        return f"<Usuario {self.nombre} - {self.email}>"

    def set_password(self, password):
        """Establecer la contraseña hasheada"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Verificar la contraseña"""
        return check_password_hash(self.password, password)

# Modelo para la tabla 'canchas'
class Cancha(db.Model):
    __tablename__ = 'canchas'  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True)  # ID de la cancha
    name = db.Column(db.String(255), nullable=False)  # Nombre de la cancha
    image = db.Column(db.String(255), nullable=False)  # Imagen de la cancha
    price_per_hour = db.Column(Numeric(10, 2), nullable=False)  # Precio por hora (usando Numeric)

    def __repr__(self):
        return f"<Cancha {self.name} - {self.price_per_hour}>"


# Modelo para la tabla 'horarios'
class Horario(db.Model):
    __tablename__ = 'horarios'  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True)  # ID del horario
    cancha_id = db.Column(db.Integer, db.ForeignKey('canchas.id'), nullable=False)  # ID de la cancha
    date = db.Column(db.Date, nullable=False)  # Fecha del horario
    start_time = db.Column(db.Time, nullable=False)  # Hora de inicio
    end_time = db.Column(db.Time, nullable=False)  # Hora de finalización
    estado = db.Column(db.Enum('disponible', 'ocupado'), default='disponible')  # Estado del horario

    cancha = db.relationship('Cancha', backref=db.backref('horarios', lazy=True))  # Relación con la tabla Canchas

    def __repr__(self):
        return f"<Horario {self.date} - {self.start_time} to {self.end_time}>"

# Modelo para la tabla 'reservaciones'
class Reservacion(db.Model):
    __tablename__ = 'reservaciones'  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True)  # ID de la reservación
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)  # ID del usuario
    horario_id = db.Column(db.Integer, db.ForeignKey('horarios.id'), nullable=False)  # ID del horario
    status = db.Column(db.Enum('pendiente', 'confirmada', 'cancelada', 'terminada'), default='pendiente')  # Estado de la reservación

    usuario = db.relationship('Usuario', backref=db.backref('reservaciones', lazy=True))  # Relación con la tabla Usuarios
    horario = db.relationship('Horario', backref=db.backref('reservaciones', lazy=True))  # Relación con la tabla Horarios

    def __repr__(self):
        return f"<Reservacion {self.id} - {self.status}>"

# Modelo para la tabla 'pagos'
class Pago(db.Model):
    __tablename__ = 'pagos'  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True)  # ID del pago
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)  # ID del usuario
    reserva_id = db.Column(db.Integer, db.ForeignKey('reservaciones.id'), nullable=False)  # ID de la reservación
    amount = db.Column(Numeric(10, 2), nullable=False)  # Monto del pago (usando Numeric)
    payment_method = db.Column(db.Enum('efectivo', 'pago movil', 'zelle'), nullable=False)  # Método de pago
    payment_proof = db.Column(db.String(255))  # Comprobante de pago
    payment_status = db.Column(db.Enum('pendiente', 'completado', 'rechazado'), default='pendiente')  # Estado del pago

    usuario = db.relationship('Usuario', backref=db.backref('pagos', lazy=True))  # Relación con la tabla Usuarios
    reservacion = db.relationship('Reservacion', backref=db.backref('pagos', lazy=True))  # Relación con la tabla Reservaciones

    def __repr__(self):
        return f"<Pago {self.id} - {self.amount} - {self.payment_status}>"

class Clase(db.Model):
    __tablename__ = 'clases'

    # Definir las columnas de la tabla
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)  # Nombre del profesor
    horario_id = db.Column(db.Integer, db.ForeignKey('horarios.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('pendiente', 'realizada', 'cancelada', name='status_enum'), default='pendiente')

    # Relación con la tabla 'horarios'
    horario = db.relationship('Horario', backref='clases', lazy=True)

    def __repr__(self):
        return f"<Clase {self.nombre}, Status: {self.status}>"