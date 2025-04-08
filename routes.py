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

def actualizar_reservaciones_terminadas():
    # Obtener todas las reservaciones
    reservaciones = Reservacion.query.filter(Reservacion.status != 'terminada').all()

    for reservacion in reservaciones:
        horario = Horario.query.get(reservacion.horario_id)
        if horario:
            now = datetime.now().time()  # Hora actual
            # Si la hora de finalización ya pasó y el estado no es 'terminada'
            if horario.end_time < now:
                reservacion.status = 'terminada'
                db.session.add(reservacion)

    db.session.commit()  # Guardar todos los cambios realizados

def convertir_hora_a_am_pm(hora_str):
    """Convierte una hora en formato 24 horas a formato 12 horas con AM/PM."""
    hora_obj = datetime.strptime(hora_str, "%H:%M:%S")
    return hora_obj.strftime("%I:%M %p")  # Formato AM/PM, ejemplo: '08:00 AM'



@main_routes.route('/reservas')
@admin_required
def listaReservas():
    actualizar_reservaciones_terminadas()

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

        # Definir la fecha actual
        dia_actual = datetime.today().date()

        # Obtener los horarios ocupados para la cancha y fecha específicas
        horarios_ocupados = Horario.query.filter_by(cancha_id=cancha_id, date=fecha, estado='ocupado').all()

        # Solo extraemos las horas de inicio en el formato HH:mm:ss
        horas_ocupadas = [ho.start_time.strftime('%H:%M:%S') for ho in horarios_ocupados]

        # Generar horarios disponibles (de 8:00 AM a 10:00 PM, bloques de 1 hora)
        horarios_disponibles = []
        hora_inicio = 8  # 8 AM
        hora_fin = 23  # 10 PM

        # Si la fecha no es el día actual, mostramos todos los horarios disponibles
        if fecha != dia_actual:
            for hora in range(hora_inicio, hora_fin):
                hora_inicio_horario = time(hour=hora, minute=0, second=0).strftime('%H:%M:%S')  # Formato HH:mm:ss
                if hora_inicio_horario not in horas_ocupadas:
                    horarios_disponibles.append({
                        'start_time': hora_inicio_horario
                    })

        # Si es el día actual, verificamos si la hora actual ha pasado
        else:
            for hora in range(hora_inicio, hora_fin):
                hora_inicio_horario = time(hour=hora, minute=0, second=0).strftime('%H:%M:%S')  # Formato HH:mm:ss
                if hora_inicio_horario > hora_actual_vzla and hora_inicio_horario not in horas_ocupadas:
                    horarios_disponibles.append({
                        'start_time': hora_inicio_horario
                    })

        return jsonify(horarios_disponibles)

    except Exception as e:
        print(f"Error al obtener horarios disponibles: {e}")
        return jsonify({"message": "Error al obtener los horarios", "error": str(e)}), 500

    
from flask import flash, redirect, url_for, render_template

@main_routes.route('/crear-reserva', methods=['GET', 'POST'])
@admin_required
def crear_reservacion():
    canchas = Cancha.query.all()
    current_date = datetime.today().date()
    metodos_pago = ['efectivo', 'pago movil', 'zelle', 'punto de venta']
    tasa = Tasa.query.first()

    now = datetime.now()
    current_date = now.date()

    min_date = current_date
    if now.hour >= 23:  # Mostrar el día siguiente si la hora actual es mayor o igual a las 23:00
        min_date = current_date + timedelta(days=1)

    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            canchas_ids = request.form.getlist('canchas[]')
            fechas = request.form.getlist('fechas[]')
            horas_inicio = request.form.getlist('horas_inicio[]')
            horas_final = request.form.getlist('horas_final[]')
            metodo_pago = request.form.get('metodo_pago')
            montos = request.form.getlist('montos[]')

            # Validaciones básicas
            if not all([canchas_ids, fechas, horas_inicio, horas_final, metodo_pago, montos]):
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('main.crear_reservacion'))

            # Verificar que todos los arrays tengan la misma longitud
            if len(set([len(canchas_ids), len(fechas), len(horas_inicio), len(horas_final), len(montos)])) != 1:
                flash('Datos inconsistentes en el formulario', 'error')
                return redirect(url_for('main.crear_reservacion'))

            # Validar montos
            total = 0
            for monto in montos:
                try:
                    monto_float = float(monto)
                    if monto_float <= 0:
                        flash('El monto debe ser mayor que cero', 'error')
                        return redirect(url_for('main.crear_reservacion'))
                    total += monto_float
                except ValueError:
                    flash('Monto inválido', 'error')
                    return redirect(url_for('main.crear_reservacion'))

            # Crear el pago (solo uno para todas las reservaciones)
            pago = Pago(
                user_id=current_user.id,
                amount=total,
                payment_method=metodo_pago,
                payment_status='completado',
                payment_proof="Admin",
                tasa_valor=tasa.monto
            )
            db.session.add(pago)
            db.session.flush()

            # Procesar cada reservación
            reservaciones_creadas = 0
            for i in range(len(canchas_ids)):
                cancha_id = canchas_ids[i]
                fecha = fechas[i]
                hora_inicio = horas_inicio[i]
                hora_fin = horas_final[i]
                monto = montos[i]

                # Convertir horas
                hora_inicio_obj = datetime.strptime(hora_inicio, "%H:%M:%S").time()
                hora_fin_obj = datetime.strptime(hora_fin, "%H:%M:%S").time()
                fecha_datetime = datetime.strptime(fecha, "%Y-%m-%d")

                # Validar que la hora final sea mayor que la hora inicial
                if hora_fin_obj <= hora_inicio_obj:
                    db.session.rollback()
                    flash('La hora final debe ser mayor que la hora de inicio', 'error')
                    return redirect(url_for('main.crear_reservacion'))

                # Validar que la fecha no sea en el pasado
                if fecha_datetime.date() < current_date:
                    db.session.rollback()
                    flash('No se pueden hacer reservaciones en fechas pasadas', 'error')
                    return redirect(url_for('main.crear_reservacion'))

                # Validar que la fecha y hora no sean en el mismo día pero hora pasada
                if fecha_datetime.date() == current_date:
                    hora_actual = now.time()
                    if hora_inicio_obj < hora_actual:
                        db.session.rollback()
                        flash('No se pueden hacer reservaciones en horas pasadas para el día actual', 'error')
                        return redirect(url_for('main.crear_reservacion'))

                # Crear reservaciones por cada hora
                current_time = hora_inicio_obj
                while current_time < hora_fin_obj:
                    next_time = (datetime.combine(datetime.min, current_time) + timedelta(hours=1)).time()

                    # Verificar disponibilidad para este segmento
                    horario_ocupado = Horario.query.filter_by(
                        cancha_id=cancha_id,
                        date=fecha_datetime
                    ).filter(
                        (Horario.start_time < next_time) &
                        (Horario.end_time > current_time) &
                        (Horario.estado == 'ocupado')
                    ).first()

                    if horario_ocupado:
                        db.session.rollback()
                        # Convertir a formato AM/PM manualmente
                        def format_ampm(time_obj):
                            hora = time_obj.hour
                            minutos = time_obj.minute
                            ampm = 'AM' if hora < 12 else 'PM'
                            hora_12 = hora if hora <= 12 else hora - 12
                            if hora_12 == 0:  # Medianoche es 12 AM
                                hora_12 = 12
                            return f"{hora_12}:{minutos:02d} {ampm}"
                        
                        hora_inicio_ampm = format_ampm(current_time)
                        hora_fin_ampm = format_ampm(next_time)
                        
                        flash(f'La cancha no está disponible entre {hora_inicio_ampm} y {hora_fin_ampm}', 'error')
                        return redirect(url_for('main.crear_reservacion'))

                    # Crear horario y reservación
                    horario = Horario(
                        cancha_id=cancha_id,
                        date=fecha_datetime,
                        start_time=current_time,
                        end_time=next_time,
                        estado='ocupado'
                    )
                    db.session.add(horario)
                    db.session.flush()

                    reservacion = Reservacion(
                        user_id=current_user.id,
                        horario_id=horario.id,
                        pago_id=pago.id,
                        status='confirmada'
                    )
                    db.session.add(reservacion)
                    reservaciones_creadas += 1

                    current_time = next_time

            db.session.commit()

            # Mensaje de éxito
            flash(f'Se crearon {reservaciones_creadas} reservaciones con éxito con un pago total de ${total:.2f}', 'success')
            return redirect(url_for('main.crear_reservacion'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear las reservas: {str(e)}', 'error')
            return redirect(url_for('main.crear_reservacion'))

    return render_template('crear-reserva.html', 
                         canchas=canchas, 
                         current_date=current_date, 
                         metodos_pago=metodos_pago,
                         min_date=min_date)

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
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        # Obtener el pago
        pago = db.session.get(Pago, pago_id)
        if not pago:
            raise ValueError("Pago no encontrado")

        # Obtener nuevo estado del formulario
        new_status = request.form.get('payment_status')
        if new_status not in ['pendiente', 'completado', 'rechazado']:
            raise ValueError("Estado de pago no válido")

        # Actualizar estado del pago
        pago.payment_status = new_status
        db.session.commit()

        # Si el pago es completado, cambia el estado de las reservaciones a confirmada
        if new_status == 'completado':
            reservaciones = Reservacion.query.filter_by(pago_id=pago.id).all()
            for reservacion in reservaciones:
                reservacion.status = 'confirmada'
                db.session.add(reservacion)

                horario = Horario.query.get(reservacion.horario_id)
                if horario:
                    horario.estado = 'ocupado'
                    db.session.add(horario)

        # Si el pago es completado, cambia el estado de las reservaciones a confirmada
        if new_status == 'pendiente':
            reservaciones = Reservacion.query.filter_by(pago_id=pago.id).all()
            for reservacion in reservaciones:
                reservacion.status = 'pendiente'
                db.session.add(reservacion)

                horario = Horario.query.get(reservacion.horario_id)
                if horario:
                    horario.estado = 'ocupado'
                    db.session.add(horario)                    

        # Si el pago es rechazado, cambia el estado de las reservaciones a cancelada y los horarios a disponibles
        elif new_status == 'rechazado':
            reservaciones = Reservacion.query.filter_by(pago_id=pago.id).all()
            for reservacion in reservaciones:
                reservacion.status = 'cancelada'
                db.session.add(reservacion)

                horario = Horario.query.get(reservacion.horario_id)
                if horario:
                    horario.estado = 'disponible'
                    db.session.add(horario)

        # Verificar si las reservaciones ya pasaron su hora de finalización
        now = datetime.now().time()
        for reservacion in reservaciones:
            horario = Horario.query.get(reservacion.horario_id)
            if horario and horario.end_time < now and reservacion.status != 'terminada':
                reservacion.status = 'terminada'
                db.session.add(reservacion)

        db.session.commit()
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': f"Estado del pago actualizado a {new_status}."
            }), 200

        flash(f"Estado del pago actualizado a {new_status}", 'success')

    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
        flash(str(e), 'danger')

    return redirect(url_for('main.pagos'))


@main_routes.route('/crear-clase', methods=['GET', 'POST'])
@admin_required
def crear_clase():
    canchas = Cancha.query.all()
    now = datetime.now()
    current_date = now.date()
    min_date = current_date if now.hour < 23 else current_date + timedelta(days=1)

    if request.method == 'POST':
        try:
            nombre_profesor = request.form.get('nombre_profesor')
            cancha_id = request.form.get('cancha')
            fecha_str = request.form.get('fecha')
            hora_inicio_str = request.form.get('hora_inicio')
            hora_fin_str = request.form.get('hora_final')

            # Validaciones básicas
            if not all([nombre_profesor, cancha_id, fecha_str, hora_inicio_str, hora_fin_str]):
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('main.crear_clase'))

            fecha_datetime = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            hora_inicio_obj = datetime.strptime(hora_inicio_str, "%H:%M:%S").time()
            hora_fin_obj = datetime.strptime(hora_fin_str, "%H:%M:%S").time()

            if hora_fin_obj <= hora_inicio_obj:
                flash('La hora de finalización debe ser posterior a la hora de inicio.', 'error')
                return redirect(url_for('main.crear_clase'))

            start_datetime = datetime.combine(fecha_datetime, hora_inicio_obj)
            end_datetime = datetime.combine(fecha_datetime, hora_fin_obj)

            current_time = hora_inicio_obj
            clases_creadas = 0

            while current_time < hora_fin_obj:
                next_time = (datetime.combine(datetime.min, current_time) + timedelta(hours=1)).time()
                if next_time > hora_fin_obj:
                    next_time = hora_fin_obj

                # Verificar disponibilidad
                horario_ocupado = Horario.query.filter_by(
                    cancha_id=cancha_id,
                    date=fecha_datetime
                ).filter(
                    (Horario.start_time < next_time) &
                    (Horario.end_time > current_time) &
                    (Horario.estado == 'ocupado')
                ).first()

                if horario_ocupado:
                    db.session.rollback()
                    flash(f'La cancha no está disponible entre {current_time.strftime("%H:%M")} y {next_time.strftime("%H:%M")}', 'error')
                    return redirect(url_for('main.crear_clase'))

                # Crear horario
                horario = Horario(
                    cancha_id=cancha_id,
                    date=fecha_datetime,
                    start_time=current_time,
                    end_time=next_time,
                    estado='ocupado'
                )
                db.session.add(horario)
                db.session.flush()

                # Crear clase
                clase = Clase(
                    nombre=nombre_profesor,
                    horario_id=horario.id,
                    status='pendiente'
                )
                db.session.add(clase)
                clases_creadas += 1

                current_time = next_time

            db.session.commit()
            
            # En lugar de hacer redirect inmediato, renderizamos la plantilla con el mensaje
            flash(f'Se crearon {clases_creadas} horarios para la clase con éxito', 'success')
            return render_template('crear-clase.html', 
                                canchas=canchas, 
                                min_date=min_date,
                                success_message=f'Se crearon {clases_creadas} horarios para la clase con éxito')

        except ValueError:
            flash('Formato de fecha u hora incorrecto.', 'error')
            return redirect(url_for('main.crear_clase'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la clase: {str(e)}', 'error')
            return redirect(url_for('main.crear_clase'))

    return render_template('crear-clase.html', canchas=canchas, min_date=min_date)

@main_routes.route('/update_clase_status/<int:clase_id>', methods=['POST'])
@admin_required
def update_clase_status(clase_id):
    # Verificar si la solicitud es AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        # Buscar la clase en la base de datos
        clase = db.session.get(Clase, clase_id)
        
        if not clase:
            raise ValueError("Clase no encontrada")

        # Obtener el nuevo estado del formulario
        new_status = request.form.get('status')
        
        if new_status not in ['pendiente', 'realizada', 'cancelada']:
            raise ValueError("Estado de clase no válido")
        
        # Actualizar el estado de la clase
        clase.status = new_status
        
        # Actualizar el estado del horario según el nuevo estado
        if new_status == 'cancelada':
            clase.horario.estado = 'disponible'
        else:  # pendiente o realizada
            clase.horario.estado = 'ocupado'
        
        db.session.commit()

        if is_ajax:
            return jsonify({
                'success': True,
                'message': f"Estado de la clase actualizado a {new_status} con éxito",
                'horario_status': clase.horario.estado  # Opcional: enviar el nuevo estado del horario
            }), 200

        flash(f"Estado de la clase actualizado a {new_status} con éxito. Horario marcado como {clase.horario.estado}.", 'success')

    except Exception as e:
        db.session.rollback()
        
        if is_ajax:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

        flash(str(e), 'danger')

    return redirect(url_for('main.clases'))

@main_routes.route('/tasa', methods=['GET', 'POST'])
@admin_required
def tasa_bs():
    tasa = Tasa.query.first()  # Obtener la tasa actual de la base de datos

    if tasa:
        # Formateamos la fecha y hora (sin segundos) a formato YYYY-MM-DD y hora en formato de 12 horas con AM/PM
        tasa_fecha_actualizacion = tasa.fecha_actualizacion.strftime('%Y-%m-%d %I:%M %p')  # Fecha y hora en formato 12 horas

    if request.method == 'POST':
        try:
            nuevo_monto = request.form['monto']
            if tasa:
                tasa.monto = float(nuevo_monto)
                db.session.commit()
                flash('Tasa actualizada con éxito', 'success')
            else:
                flash('No se encontró la tasa', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la tasa: {str(e)}', 'danger')
        
        return redirect(url_for('main.tasa_bs'))  # Redirigir a la misma vista

    return render_template('tasa.html', tasa=tasa, tasa_fecha_actualizacion=tasa_fecha_actualizacion)

@main_routes.route('/', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            # Buscar al usuario por su correo electrónico
            usuario = db.session.query(Usuario).filter_by(email=email).first()

            # Si el usuario existe y la contraseña es correcta
            if usuario:
                if usuario.check_password(password):
                    # Verificar si el usuario está bloqueado
                    if usuario.isBlocked:
                        flash('Tu cuenta está bloqueada. No puedes iniciar sesión.', 'danger')
                        return redirect(url_for('main.login'))

                    login_user(usuario)  # Inicia la sesión del usuario
                    flash('Inicio de sesión exitoso', 'success')

                    # Redirigir a la página correspondiente según el rol del usuario
                    if usuario.role == 'admin':
                        return redirect(url_for('main.listaReservas'))  # Página de administración
                    else:
                        flash('No tienes acceso de administrador', 'danger')
                        return redirect(url_for('main.login'))
                else:
                    flash('Contraseña incorrecta', 'danger')
            else:
                flash('Correo electrónico no registrado', 'danger')

    except Exception as e:
        # Si ocurre un error inesperado, mostrar un error por defecto
        flash('Ocurrió un error inesperado. Por favor, inténtalo de nuevo más tarde.', 'danger')

    return render_template('login.html')


@main_routes.route('/logout')
@admin_required
def logout():
    logout_user()  # Cierra la sesión
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('main.login'))
