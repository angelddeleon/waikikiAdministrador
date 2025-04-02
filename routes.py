from flask import Flask, render_template, redirect, url_for, request, flash, Blueprint, jsonify
from models import db, Usuario, Pago, Reservacion, Horario, Cancha, Clase, Tasa
from datetime import datetime, time, timedelta
from flask_login import login_user, login_required, current_user, logout_user
from functools import wraps
import pytz

main_routes = Blueprint('main', __name__)

# Decorador para verificar si el usuario es admin
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('main.login'))  # Redirigir al login si no es admin
        return f(*args, **kwargs)
    return decorated_function


@main_routes.route('/reservas')
@admin_required
def listaReservas():
    # Usamos un join para obtener las reservaciones con los usuarios y horarios relacionados
    reservas = db.session.query(Reservacion).join(Usuario).join(Horario).all()

    # Formatear las horas a 12 horas con AM/PM
    for reservacion in reservas:
        # Obtener las horas de inicio y fin
        start_time = reservacion.horario.start_time
        end_time = reservacion.horario.end_time
        
        # Si las horas son objetos `time`, los convertimos en objetos `datetime` para formatearlos
        start_time_formatted = datetime.combine(datetime.today(), start_time).strftime("%I:%M %p")
        end_time_formatted = datetime.combine(datetime.today(), end_time).strftime("%I:%M %p")
        
        # Añadir las horas formateadas a las reservaciones
        reservacion.start_time_formatted = start_time_formatted
        reservacion.end_time_formatted = end_time_formatted

    return render_template('reservas-datatable.html', reservas=reservas)


@main_routes.route('/clases')
@admin_required
def clases():

    try:
        # Obtener todas las clases de la base de datos, incluyendo sus horarios y canchas
        clases = Clase.query.join(Horario).join(Cancha).all()  # Asegurándote de hacer el join correctamente

        print(f"Clases recuperadas: {clases}")  # Para depuración

        if not clases:
            flash('No hay clases registradas', 'warning')

        # Pasa las clases al template
        return render_template('clases-datatable.html', clases=clases)
    
    except Exception as e:
        flash(f'Error al obtener las clases: {str(e)}', 'danger')
        return render_template('clases-datatable.html', clases=[])


@main_routes.route('/pagos')
@admin_required
def pagos():
    try:
        # Obtener todos los pagos de la base de datos
        pagos = db.session.query(Pago).outerjoin(Reservacion, Pago.id == Reservacion.pago_id).all()

        # Si no hay pagos, se puede mostrar un mensaje
        if not pagos:
            flash('No hay pagos registrados', 'warning')
        
        # Pasa los pagos al template
        return render_template('pagos-datatable.html', pagos=pagos)
    
    except Exception as e:
        flash(f'Error al obtener los pagos: {str(e)}', 'danger')
        return render_template('pagos-datatable.html', pagos=[])

@main_routes.route('/obtener_horas_disponibles', methods=['GET'])
def obtener_horas_disponibles():
    # Obtener los parámetros del request
    cancha_id = request.args.get('cancha_id')
    fecha_str = request.args.get('fecha')

    if not cancha_id or not fecha_str:
        return jsonify({"message": "Faltan parámetros: cancha_id y fecha"}), 400

    try:
        # Convertir la fecha en formato string a tipo datetime
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"message": "Formato de fecha incorrecto (YYYY-MM-DD)"}), 400

    try:
        # Definir la zona horaria de Venezuela (America/Caracas)
        vzla_timezone = pytz.timezone("America/Caracas")

        # Obtener la hora actual en la zona horaria de Venezuela
        hora_actual_vzla = datetime.now(vzla_timezone).strftime("%H:%M:%S")

        hora_str = "10:00:00"
        hora_obj = datetime.strptime(hora_str, "%H:%M:%S").time()

        # Convertir la hora actual a formato 8:00:00 (HH:mm:ss)
        hora_formateada = hora_obj.strftime("%H:%M:%S")

        print("HORAAAA " + hora_actual_vzla)  # Ejemplo de salida: 08:15:30


        # Obtener los horarios ocupados para la cancha y fecha específicas
        horarios_ocupados = Horario.query.filter_by(cancha_id=cancha_id, date=fecha, estado='ocupado').all()
        # Solo extraemos las horas de inicio en el formato HH:mm:ss
        horas_ocupadas = [ho.start_time.strftime('%H:%M:%S') for ho in horarios_ocupados]

        # Generar horarios disponibles (de 8:00 AM a 10:00 PM, bloques de 1 hora)
        horarios_disponibles = []
        hora_inicio = 8  # 8 AM
        hora_fin = 23  # 10 PM

        for hora in range(hora_inicio, hora_fin):
            hora_inicio_horario = time(hour=hora, minute=0, second=0).strftime('%H:%M:%S')  # Formato HH:mm:ss

            # Verificar si el horario está ocupado
            if hora_inicio_horario not in horas_ocupadas and hora_inicio_horario > hora_actual_vzla:
                horarios_disponibles.append({
                    'start_time': hora_inicio_horario
                })

        return jsonify(horarios_disponibles)

    except Exception as e:
        print(f"Error al obtener horarios disponibles: {e}")
        return jsonify({"message": "Error al obtener los horarios", "error": str(e)}), 500

@main_routes.route('/crear-reserva', methods=['GET', 'POST'])
@admin_required
def crear_reservacion():
    canchas = Cancha.query.all()
    current_date = datetime.today().date()
    metodos_pago = ['efectivo', 'pago movil', 'zelle', 'punto de venta']
    tasa = Tasa.query.first()

    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            cancha_id = request.form.get('cancha')
            fecha = request.form.get('fecha')
            hora_inicio = request.form.get('hora_inicio')  # Formato HH:MM:SS
            hora_fin = request.form.get('hora_final')      # Formato HH:MM:SS
            metodo_pago = request.form.get('metodo_pago')
            monto = float(request.form.get('monto'))

            # Convertir fechas y horas
            try:
                hora_inicio_obj = datetime.strptime(hora_inicio, "%H:%M:%S").time()
                hora_fin_obj = datetime.strptime(hora_fin, "%H:%M:%S").time()
            except ValueError:
                flash('Formato de hora incorrecto. Use HH:MM:SS', 'danger')
                return redirect(url_for('main.crear_reservacion'))

            fecha_datetime = datetime.strptime(fecha, "%Y-%m-%d")

            # Verificar disponibilidad de la cancha
            horarios_ocupados = Horario.query.filter_by(
                cancha_id=cancha_id,
                date=fecha_datetime
            ).filter(
                (Horario.start_time < hora_fin_obj) & 
                (Horario.end_time > hora_inicio_obj) &
                (Horario.estado == 'ocupado')
            ).all()

            if horarios_ocupados:
                flash('La cancha no está disponible en el horario seleccionado', 'danger')
                return redirect(url_for('main.crear_reservacion'))

            # Crear el pago (único para todas las reservaciones)
            pago = Pago(
                user_id=current_user.id,
                amount=monto,
                payment_method=metodo_pago,
                payment_status='completado',
                payment_proof="Admin",
                tasa_valor=tasa.monto
            )
            db.session.add(pago)
            db.session.flush()  # Para obtener el ID del pago

            # Crear un horario continuo para toda la reserva
            horario = Horario(
                cancha_id=cancha_id,
                date=fecha_datetime,
                start_time=hora_inicio_obj,
                end_time=hora_fin_obj,
                estado='ocupado'
            )
            db.session.add(horario)
            db.session.flush()

            # Crear la reservación principal asociada al pago
            reservacion = Reservacion(
                user_id=current_user.id,
                horario_id=horario.id,
                pago_id=pago.id,
                status='confirmada'
            )
            db.session.add(reservacion)

            # Si necesitas crear múltiples reservaciones de 1 hora (opcional)
            # current_time = hora_inicio_obj
            # while current_time < hora_fin_obj:
            #     next_time = (datetime.combine(datetime.min, current_time) + timedelta(hours=1)).time()
            #     if next_time > hora_fin_obj:
            #         next_time = hora_fin_obj
                
            #     # Crear horario para cada segmento
            #     horario_segmento = Horario(
            #         cancha_id=cancha_id,
            #         date=fecha_datetime,
            #         start_time=current_time,
            #         end_time=next_time,
            #         estado='ocupado'
            #     )
            #     db.session.add(horario_segmento)
            #     db.session.flush()
                
            #     # Crear reservación asociada al mismo pago
            #     reservacion_segmento = Reservacion(
            #         user_id=current_user.id,
            #         horario_id=horario_segmento.id,
            #         pago_id=pago.id,
            #         status='confirmada'
            #     )
            #     db.session.add(reservacion_segmento)
                
            #     current_time = next_time

            db.session.commit()
            flash('Reserva creada con éxito', 'success')
            return redirect(url_for('main.listaReservas'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la reserva: {str(e)}', 'danger')
            return redirect(url_for('main.crear_reservacion'))

    return render_template('crear-reserva.html', 
                         canchas=canchas, 
                         current_date=current_date, 
                         metodos_pago=metodos_pago)


@main_routes.route('/usuarios')
@admin_required
def listaUsuarios():

    usuarios = db.session.query(Usuario).all()  # Obtiene todos los usuarios
    return render_template('usuarios-datatable.html', usuarios=usuarios)


# Ruta para bloquear/desbloquear un usuario

@main_routes.route('/toggle_block/<int:user_id>', methods=['POST'])
@admin_required
def toggle_block(user_id):

    usuario = db.session.get(Usuario, user_id)

    if usuario:
        # Cambiar el estado de 'isBlocked'
        usuario.isBlocked = not usuario.isBlocked
        db.session.commit()

        flash('El usuario ha sido bloqueado/desbloqueado correctamente', 'success')
    else:
        flash('No se encontró el usuario', 'danger')

    return redirect(url_for('main.listaUsuarios'))


@main_routes.route('/update_payment_status/<int:pago_id>', methods=['POST'])
@admin_required
def update_payment_status(pago_id):

    # Obtener el pago de la base de datos usando el ID
    pago = db.session.get(Pago, pago_id)

    if pago:
        # Obtener el nuevo estado del formulario
        new_status = request.form.get('payment_status')
        
        if new_status:
            # Actualizar el estado del pago
            pago.payment_status = new_status
            db.session.commit()  # Guardar los cambios en la base de datos
            
            flash('Estado del pago actualizado con éxito', 'success')
        else:
            flash('Estado de pago no válido', 'danger')
    else:
        flash('Pago no encontrado', 'danger')

    return redirect(url_for('main.pagos'))


@main_routes.route('/crear-clase', methods=['GET', 'POST'])
@admin_required
def crear_clase():

    horas_disponibles = []
    canchas = Cancha.query.all()  # Obtener todas las canchas de la base de datos
    current_date = datetime.today().date()

    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        cancha_id = request.form.get('cancha')
        fecha = request.form.get('fecha')
        hora_inicio = request.form.get('hora_inicio')
        status = request.form.get('status')

        # Obtener la cancha y el horario
        cancha = db.session.get(Cancha, cancha_id)
        hora_inicio = datetime.strptime(hora_inicio, "%H:%M:%S").time()
        hora_fin_obj = (datetime.combine(datetime.today(), hora_inicio) + timedelta(hours=1)).time()

        # Crear el horario ocupado
        fecha_datetime = datetime.strptime(fecha, "%Y-%m-%d")  # Cambiado a "%Y-%m-%d"
        horario = Horario(
            cancha_id=cancha.id,
            date=fecha_datetime,
            start_time=hora_inicio,
            end_time=hora_fin_obj.strftime('%H:%M:%S'),  # Almacenar hora de fin
            estado='ocupado'  # Cambiar el estado a 'ocupado'
        )

        try:
            # Agregar el horario a la base de datos
            db.session.add(horario)
            db.session.commit()

            # Crear la clase y asociarla con el horario creado
            clase = Clase(
                nombre=nombre,
                horario_id=horario.id,  # Asignar el ID del horario creado
                status=status
            )
            db.session.add(clase)
            db.session.commit()

            flash('Clase creada con éxito', 'success')
            return redirect(url_for('main.clases'))

        except Exception as e:
            db.session.rollback()  # Revertir los cambios si ocurre un error
            flash(f'Error al crear la clase: {str(e)}', 'danger')
            return redirect(url_for('main.crear_clase'))

    return render_template('crear-clase.html', canchas=canchas, current_date=current_date, horas_disponibles=horas_disponibles)


@main_routes.route('/update_clase_status/<int:clase_id>', methods=['POST'])
@admin_required
def update_clase_status(clase_id):

    # Buscar la clase en la base de datos
    clase = db.session.get(Clase, clase_id)

    if clase:
        # Obtener el nuevo estado del formulario
        new_status = request.form.get('status')
        # Actualizar el estado de la clase
        clase.status = new_status
        db.session.commit()

        flash('Estado de la clase actualizado con éxito', 'success')
    else:
        flash('Clase no encontrada', 'danger')

    return redirect(url_for('main.clases'))


@main_routes.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Buscar al usuario por su correo electrónico
        usuario = db.session.query(Usuario).filter_by(email=email).first()

        if usuario and usuario.check_password(password):
            login_user(usuario)  # Inicia la sesión del usuario
            flash('Inicio de sesión exitoso', 'success')

            # Verificamos si el usuario tiene el rol de admin
            if usuario.role == 'admin':
                return redirect(url_for('main.listaReservas'))  # Página de administración
            else:
                flash('No tienes acceso de administrador', 'danger')
                return redirect(url_for('main.login'))
        else:
            flash('Correo o contraseña incorrectos', 'danger')
    
    return render_template('login.html')


@main_routes.route('/logout')
@admin_required
def logout():
    logout_user()  # Cierra la sesión
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('main.login'))
