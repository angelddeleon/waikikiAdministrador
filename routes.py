from flask import Flask, render_template, redirect, url_for, request, flash, Blueprint, jsonify
from models import db, Usuario, Pago, Reservacion, Horario, Cancha, Clase
import requests
from datetime import datetime, time, timedelta
import os
from werkzeug.utils import secure_filename

main_routes = Blueprint('main', __name__)

@main_routes.route('/reservas')
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


@main_routes.route('/update_reservation_status/<int:reservacion_id>', methods=['POST'])
def update_reservation_status(reservacion_id):
    # Buscar la reservación en la base de datos
    reservacion = Reservacion.query.get(reservacion_id)

    if reservacion:
        # Obtener el nuevo estado del formulario
        new_status = request.form.get('status')
        # Actualizar el estado de la reservación
        reservacion.status = new_status
        db.session.commit()

        flash('Estado de la reservación actualizado con éxito', 'success')
    else:
        flash('Reservación no encontrada', 'danger')

    return redirect(url_for('main.listaReservas'))

@main_routes.route('/clases')
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
def pagos():
    try:
        # Obtener todos los pagos de la base de datos
        pagos = Pago.query.all()  # Obtiene todos los pagos registrados en la base de datos

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
    fecha = request.args.get('fecha')  # Fecha seleccionada
    cancha_id = request.args.get('cancha_id')  # ID de la cancha seleccionada

    # Verificar si la fecha se ha pasado correctamente
    if not fecha:
        flash('La fecha es obligatoria', 'danger')
        return redirect(url_for('main.crear_reservacion'))

    # Convertir la fecha de string a datetime usando el formato correcto
    try:
        fecha_datetime = datetime.strptime(fecha, "%Y-%m-%d")  # Cambiado a %Y-%m-%d
    except ValueError:
        flash('Formato de fecha incorrecto', 'danger')
        return redirect(url_for('main.crear_reservacion'))

    # Obtener la cancha y su precio
    cancha = Cancha.query.get(cancha_id)

    # Obtener los horarios ocupados para esa cancha y fecha
    horarios_ocupados = db.session.query(Horario).filter_by(cancha_id=cancha_id, date=fecha_datetime.date(), estado='ocupado').all()

    # Generar los horarios disponibles de 8:00 AM a 10:00 PM
    horas_disponibles = []
    for h in range(8, 22):  # De 8:00 AM a 10:00 PM
        hora_inicio_obj = time(h, 0)  # Hora completa (ejemplo: 08:00)
        hora_fin_obj = time(h + 1, 0)  # Hora de fin es una hora después (ejemplo: 09:00)

        # Verificar si el horario está ocupado
        horario_ocupado = any(horario.start_time == hora_inicio_obj for horario in horarios_ocupados)

        if not horario_ocupado:
            # Crear un diccionario con los datos requeridos para el frontend
            start_time_formatted = hora_inicio_obj.strftime('%H:%M:%S')
            start_time_display = hora_inicio_obj.strftime('%I:%M%p').lstrip("0").replace("AM", "AM").replace("PM", "PM")
            horas_disponibles.append({
                'start_time': start_time_formatted,
                'start_time_display': start_time_display,
                'end_time': hora_fin_obj.strftime('%H:%M:%S'),
            })

    return jsonify(horas_disponibles)

@main_routes.route('/crear-reserva', methods=['GET', 'POST'])
def crear_reservacion():
    horas_disponibles = []  # Inicializamos la variable horas_disponibles
    canchas = Cancha.query.all()  # Asegúrate de obtener todas las canchas de la base de datos
    current_date = datetime.today().date()

    if request.method == 'POST':
        # Obtener datos del formulario
        cancha_id = request.form.get('cancha')
        if not cancha_id:
            flash('Por favor, selecciona una cancha', 'danger')
            return redirect(url_for('main.crear_reservacion'))  # Aquí ya hay un return si la cancha no está seleccionada

        fecha = request.form.get('fecha')
        hora_inicio = request.form.get('hora_inicio')
        metodo_pago = request.form.get('metodo_pago')
        comprobante = "Admin"
        monto = request.form.get('monto')

        # Obtener la cancha por ID
        cancha = Cancha.query.get(cancha_id)

        if not cancha:
            flash('La cancha seleccionada no existe.', 'danger')
            return redirect(url_for('main.crear_reservacion'))  # Aquí también hay un return si la cancha no existe

        # Convertir la fecha y hora de inicio a datetime
        hora_inicio = datetime.strptime(hora_inicio, "%H:%M:%S").time()
        hora_fin_obj = (datetime.combine(datetime.today(), hora_inicio) + timedelta(hours=1)).time()  # Sumar una hora
        
        # Convertir la fecha en formato año-mes-día
        fecha_datetime = datetime.strptime(fecha, "%Y-%m-%d")  # Cambiado a "%Y-%m-%d"

        # Solo creamos la reservación y el pago si el comprobante fue subido con éxito
        try:
            # Crear la reservación con el primer horario disponible
            horario = Horario(
                cancha_id=cancha_id,
                date=fecha_datetime,  # Fecha en formato %Y-%m-%d
                start_time=hora_inicio,
                end_time=hora_fin_obj.strftime('%H:%M:%S'),  # Almacenamos hora de fin en formato HH:MM:SS
                estado='ocupado'
            )

            db.session.add(horario)
            db.session.commit()

            # Crear la reservación con el horario asignado
            user_id = 1  # Establecer el ID del usuario que está haciendo la reservación
            reservacion = Reservacion(user_id=user_id, horario_id=horario.id)  # Toma el primer horario disponible
            db.session.add(reservacion)
            db.session.commit()

            # Procesar el pago
            pago = Pago(
                user_id=user_id,
                reserva_id=reservacion.id,
                amount=monto,  # Accede correctamente al precio por hora de la cancha
                payment_method=metodo_pago,
                payment_status='pendiente',
                payment_proof=comprobante  # Asignamos el comprobante si se subió
            )
            db.session.add(pago)
            db.session.commit()

            flash('Reservación creada con éxito', 'success')
            return redirect(url_for('main.listaReservas'))  # Asegúrate de que hay un return aquí

        except Exception as e:
            db.session.rollback()  # Revertimos cualquier cambio si ocurre un error
            flash(f'Error al crear la reservación: {str(e)}', 'danger')
            return redirect(url_for('main.crear_reservacion'))  # Siempre tener un return en el caso de un error

    # Si la solicitud es GET, generar los horarios disponibles
    return render_template('crear-reserva.html', canchas=canchas, current_date=current_date, horas_disponibles=horas_disponibles)  # Asegúrate de que haya un return aquí


@main_routes.route('/usuarios')
def listaUsuarios():
    usuarios = Usuario.query.all()  # Obtiene todos los usuarios
    return render_template('usuarios-datatable.html', usuarios=usuarios)

# Ruta para bloquear/desbloquear un usuario
@main_routes.route('/toggle_block/<int:user_id>', methods=['POST'])
def toggle_block(user_id):
    usuario = Usuario.query.get(user_id)

    if usuario:
        # Cambiar el estado de 'isBlocked'
        usuario.isBlocked = not usuario.isBlocked
        db.session.commit()

        flash('El usuario ha sido bloqueado/desbloqueado correctamente', 'success')
    else:
        flash('No se encontró el usuario', 'danger')

    return redirect(url_for('main.listaUsuarios'))

@main_routes.route('/update_payment_status/<int:pago_id>', methods=['POST'])
def update_payment_status(pago_id):
    # Obtener el pago de la base de datos usando el ID
    pago = Pago.query.get(pago_id)

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

    # Redirigir a la página de pagos (o donde sea que quieras redirigir)
    return redirect(url_for('main.pagos'))


@main_routes.route('/crear-clase', methods=['GET', 'POST'])
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
        cancha = Cancha.query.get(cancha_id)
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
def update_clase_status(clase_id):
    # Buscar la clase en la base de datos
    clase = Clase.query.get(clase_id)

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
    return render_template('login.html')


