from flask import Flask, render_template, redirect, url_for, request, flash, Blueprint, jsonify
from models import db, Usuario, Pago, Reservacion, Horario, Cancha
from datetime import datetime

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

@main_routes.route('/pagos')
def pagos():
    pagos = Pago.query.all()  # Obtiene todos los pagos
    return render_template('pagos-datatable.html', pagos=pagos)

@main_routes.route('/crear-reserva', methods=['GET', 'POST'])
def crear_reservacion():
    if request.method == 'POST':
        # Obtener datos del formulario
        cancha_id = request.form['cancha']
        fecha = request.form['fecha']
        hora_inicio = request.form['hora_inicio']
        metodo_pago = request.form['metodo_pago']
        comprobante = request.files['comprobante']

        # Convertir la fecha y hora de inicio
        fecha_datetime = datetime.strptime(f"{fecha} {hora_inicio}", "%Y-%m-%d %H:%M")

        # Obtener la cancha y su precio
        cancha = Cancha.query.get(cancha_id)
        hora_fin = (fecha_datetime.hour + 1) % 24
        hora_fin_str = f"{hora_fin:02}:00"
        
        # Crear el horario de la reservación
        horario = Horario(
            cancha_id=cancha_id,
            date=fecha_datetime.date(),
            start_time=fecha_datetime.time(),
            end_time=hora_fin_str
        )
        db.session.add(horario)
        db.session.commit()

        # Crear la reservación
        user_id = 1  # Aquí debes obtener el id del usuario actual
        reservacion = Reservacion(user_id=user_id, horario_id=horario.id)
        db.session.add(reservacion)
        db.session.commit()

        # Procesar el pago
        pago = Pago(
            user_id=user_id,
            reserva_id=reservacion.id,
            amount=cancha.price_per_hour,
            payment_method=metodo_pago,
            payment_proof=comprobante.filename,
            payment_status='pendiente'
        )
        db.session.add(pago)
        db.session.commit()

        # Guardar el comprobante de pago
        if comprobante:
            comprobante.save(os.path.join('uploads', comprobante.filename))

        return redirect(url_for('reservaciones'))

    # Obtener todas las canchas disponibles
    canchas = Cancha.query.all()
    current_date = datetime.today().date()

    return render_template('crear_reserva.html', canchas=canchas, current_date=current_date)

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
