from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
import tempfile
import pandas as pd
import io
import base64
from flask import send_file

# 1. Creación de la aplicación Flask
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True # Para forzar la recarga de plantillas

# 2. Configuración de la aplicación
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plate_recognition.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 3. Importación de módulos locales
from models import User, Vehicle, AccessLog, db
from plate_recognition import PlateRecognitionService
from auth import require_role

# 4. Vinculación de la base de datos
db.init_app(app)

# 5. Inicialización de otros servicios
plate_service = PlateRecognitionService()

# Crear directorios necesarios al iniciar
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True) # Asegurarse que la carpeta static existe


# --- Definición de Rutas de Páginas (Endpoints) ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['user_name'] = user.full_name
            return redirect(url_for('dashboard'))
        
        flash('Credenciales inválidas', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@require_role(['admin', 'security'])
def dashboard():
    return render_template('dashboard.html')

@app.route('/users')
@require_role(['admin'])
def users():
    return render_template('users.html')

@app.route('/history')
@require_role(['admin', 'security'])
def history():
    return render_template('history.html')

@app.route('/reports')
@require_role(['admin'])
def reports():
    return render_template('reports.html')


# --- Definición de Rutas de API ---

# --- API para Generar Reportes ---
@app.route("/api/generar_reporte", methods=["POST"])
@require_role(['admin'])
def api_generar_reporte():
    data = request.json or {}
    fecha_ini_str = data.get("fecha_inicio")
    fecha_fin_str = data.get("fecha_fin")

    if not fecha_ini_str or not fecha_fin_str:
        return jsonify({"success": False, "msg": "Fechas requeridas."}), 400

    try:
        # Convertir fechas de YYYY-MM-DD a objetos datetime
        fecha_inicio_dt = datetime.strptime(fecha_ini_str, "%Y-%m-%d").date()
        fecha_fin_dt = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()

        # Consulta con SQLAlchemy
        query = db.session.query(
            AccessLog.plate_number,
            AccessLog.timestamp,
            AccessLog.authorized,
            User.full_name,
            User.occupation
        ).outerjoin(User, AccessLog.user_id == User.id).filter(
            db.func.date(AccessLog.timestamp) >= fecha_inicio_dt,
            db.func.date(AccessLog.timestamp) <= fecha_fin_dt
        ).order_by(AccessLog.timestamp.desc())

        logs = query.all()

        if not logs:
            return jsonify({"success": False, "msg": "No hay registros en el rango seleccionado."}), 404

        # Preparar datos para el DataFrame
        report_data = []
        for log in logs:
            report_data.append({
                "Placa": log.plate_number,
                "Fecha": log.timestamp.strftime('%Y-%m-%d'),
                "Hora": log.timestamp.strftime('%H:%M:%S'),
                "Resultado": "Autorizado" if log.authorized else "Denegado",
                "Usuario": log.full_name or "Desconocido",
                "Ocupación": log.occupation or "N/A"
            })

        df = pd.DataFrame(report_data)
        
        # Crear el archivo Excel en memoria
        output = io.BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)

        filename = f"reporte_accesos_{fecha_inicio_dt.strftime('%Y%m%d')}_{fecha_fin_dt.strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500


# --- API para Gestión de Usuarios (MODIFICADA) ---

@app.route('/api/users', methods=['GET'])
@require_role(['admin'])
def get_users():
    """Obtiene todos los usuarios y su placa asociada."""
    users_with_plates = db.session.query(User, Vehicle.plate_number)\
        .outerjoin(Vehicle, User.id == Vehicle.user_id).all()
    
    users_list = []
    for user, plate_number in users_with_plates:
        users_list.append({
            'id': user.id,
            'full_name': user.full_name,
            'occupation': user.occupation,
            'role': user.role,
            'username': user.username,
            'created_at': user.created_at.isoformat(),
            'plate_number': plate_number
        })
    return jsonify(users_list)

@app.route('/api/users/<int:user_id>', methods=['GET'])
@require_role(['admin'])
def get_user(user_id):
    """Obtiene un usuario específico y su placa."""
    user = User.query.get_or_404(user_id)
    vehicle = Vehicle.query.filter_by(user_id=user.id).first()
    return jsonify({
        'id': user.id,
        'full_name': user.full_name,
        'occupation': user.occupation,
        'role': user.role,
        'username': user.username,
        'plate_number': vehicle.plate_number if vehicle else None
    })

@app.route('/api/users', methods=['POST'])
@require_role(['admin'])
def create_user():
    """Crea un nuevo usuario y, opcionalmente, su vehículo."""
    data = request.get_json()
    if not data or not data.get('full_name'):
        return jsonify({'error': 'Faltan datos requeridos'}), 400

    try:
        new_user = User(
            full_name=data['full_name'],
            occupation=data.get('occupation', 'visitante'),
            role=data.get('role', 'user'),
            username=data.get('username') or None
        )
        if data.get('password'):
            new_user.password_hash = generate_password_hash(data['password'])
        
        db.session.add(new_user)
        db.session.flush()  # Obtenemos el ID del usuario antes de hacer commit

        plate_number = data.get('plate_number')
        if plate_number:
            # Verificar si la placa ya existe
            existing_vehicle = Vehicle.query.filter_by(plate_number=plate_number).first()
            if existing_vehicle:
                raise Exception(f"La placa '{plate_number}' ya está registrada a otro usuario.")
            
            new_vehicle = Vehicle(plate_number=plate_number, user_id=new_user.id)
            db.session.add(new_vehicle)
        
        db.session.commit()
        return jsonify({'message': 'Usuario creado', 'id': new_user.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_role(['admin'])
def update_user(user_id):
    """Actualiza un usuario y su vehículo asociado."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    try:
        user.full_name = data.get('full_name', user.full_name)
        user.occupation = data.get('occupation', user.occupation)
        user.role = data.get('role', user.role)
        user.username = data.get('username', user.username)
        
        if data.get('password'):
            user.password_hash = generate_password_hash(data['password'])

        plate_number = data.get('plate_number')
        vehicle = Vehicle.query.filter_by(user_id=user.id).first()

        if plate_number:
            plate_number = plate_number.strip().upper()
            # Verificar si la placa ya existe y no pertenece a este usuario
            existing_vehicle = Vehicle.query.filter_by(plate_number=plate_number).first()
            if existing_vehicle and existing_vehicle.user_id != user.id:
                 raise Exception(f"La placa '{plate_number}' ya está registrada a otro usuario.")

            if vehicle:
                vehicle.plate_number = plate_number
            else:
                new_vehicle = Vehicle(plate_number=plate_number, user_id=user.id)
                db.session.add(new_vehicle)
        elif vehicle:
            # Si no se proporciona placa y el usuario tenía una, se elimina
            db.session.delete(vehicle)

        db.session.commit()
        return jsonify({'message': 'Usuario actualizado'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_role(['admin'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session.get('user_id'):
        return jsonify({'error': 'No puedes eliminar tu propia cuenta'}), 403
    
    # También elimina el vehículo asociado si existe
    Vehicle.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Usuario eliminado'})


# --- Otras APIs ---

@app.route('/api/manual_entry', methods=['POST'])
@require_role(['admin', 'security'])
def manual_entry():
    """Procesa una entrada de placa manual."""
    try:
        data = request.get_json()
        plate_number = data.get('plate_number')

        if not plate_number:
            return jsonify({'error': 'El número de placa es requerido'}), 400

        plate_number = plate_number.strip().upper()
        vehicle = Vehicle.query.filter_by(plate_number=plate_number).first()
        
        access_log = AccessLog(
            plate_number=plate_number,
            user_id=vehicle.user_id if vehicle else None,
            timestamp=datetime.utcnow(),
            authorized=vehicle is not None,
            confidence=1.0,
            image_path=None
        )
        db.session.add(access_log)
        db.session.commit()
        
        if vehicle:
            return jsonify({
                'success': True, 'authorized': True, 'message': 'Acceso autorizado (Entrada Manual)',
                'user': {'name': vehicle.user.full_name, 'occupation': vehicle.user.occupation},
                'plate_number': plate_number, 'confidence': 1.0
            })
        else:
            return jsonify({
                'success': True, 'authorized': False, 'message': 'Placa no registrada (Entrada Manual)',
                'plate_number': plate_number, 'confidence': 1.0
            })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/capture_frame', methods=['POST'])
@require_role(['admin', 'security'])
def capture_frame():
    """Recibe un frame en base64 desde el cliente, lo analiza y registra el acceso."""
    try:
        data = request.get_json()
        if 'image' not in data:
            return jsonify({'error': 'No se recibió ninguna imagen'}), 400

        # Decodificar la imagen base64
        # El string viene en formato 'data:image/jpeg;base64,LzlqLzRBQ...
        header, encoded = data['image'].split(',', 1)
        image_data = base64.b64decode(encoded)

        # Guardar en archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name

        try:
            # Usar el servicio de reconocimiento de placas
            plate_result = plate_service.recognize_plate(tmp_path)
            
            if not plate_result.get('success') or not plate_result.get('plate_number'):
                return jsonify({'success': False, 'message': 'No se pudo reconocer la placa.', 'confidence': 0})
            
            plate_number = plate_result['plate_number']
            confidence = plate_result['confidence']

            # --- INICIO DE DEBUG ---
            print(f"DEBUG: Placa reconocida por la API: '{plate_number}'")
            all_vehicles_in_db = Vehicle.query.all()
            all_plates_in_db = [v.plate_number for v in all_vehicles_in_db]
            print(f"DEBUG: Placas registradas en la base de datos: {all_plates_in_db}")
            # --- FIN DE DEBUG ---
            
            vehicle = Vehicle.query.filter_by(plate_number=plate_number).first()
            
            access_log = AccessLog(
                plate_number=plate_number,
                user_id=vehicle.user_id if vehicle else None,
                timestamp=datetime.utcnow(),
                authorized=vehicle is not None,
                confidence=confidence,
                image_path=None # No guardamos la imagen del stream por ahora
            )
            db.session.add(access_log)
            db.session.commit()
            
            if vehicle:
                return jsonify({
                    'success': True, 'authorized': True, 'message': 'Acceso autorizado',
                    'user': {'name': vehicle.user.full_name, 'occupation': vehicle.user.occupation},
                    'plate_number': plate_number, 'confidence': confidence
                })
            else:
                return jsonify({
                    'success': True, 'authorized': False, 'message': 'Placa no registrada - Requiere registro',
                    'plate_number': plate_number, 'confidence': confidence
                })
        
        finally:
            # Eliminar el archivo temporal después de usarlo
            os.remove(tmp_path)
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/capture_plate', methods=['POST'])
@require_role(['admin', 'security'])
def capture_plate():
    """Endpoint principal para captura y procesamiento de placas"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No se encontró imagen'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        filename = secure_filename(f"{uuid.uuid4()}_{image_file.filename}")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        
        plate_result = plate_service.recognize_plate(image_path)
        
        if not plate_result['success']:
            return jsonify({'success': False, 'message': 'No se pudo reconocer la placa', 'confidence': 0})
        
        plate_number = plate_result['plate_number']
        confidence = plate_result['confidence']
        
        vehicle = Vehicle.query.filter_by(plate_number=plate_number).first()
        
        access_log = AccessLog(
            plate_number=plate_number,
            user_id=vehicle.user_id if vehicle else None,
            timestamp=datetime.utcnow(),
            authorized=vehicle is not None,
            confidence=confidence,
            image_path=image_path
        )
        db.session.add(access_log)
        db.session.commit()
        
        if vehicle:
            return jsonify({
                'success': True, 'authorized': True, 'message': 'Acceso autorizado',
                'user': {'name': vehicle.user.full_name, 'occupation': vehicle.user.occupation},
                'plate_number': plate_number, 'confidence': confidence
            })
        else:
            return jsonify({
                'success': True, 'authorized': False, 'message': 'Placa no registrada - Requiere registro',
                'plate_number': plate_number, 'confidence': confidence
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/access_logs')
@require_role(['admin', 'security'])
def get_access_logs():
    """Obtener registros de acceso con filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = AccessLog.query
    
    if start_date:
        query = query.filter(AccessLog.timestamp >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(AccessLog.timestamp <= datetime.fromisoformat(end_date))
    
    logs = query.order_by(AccessLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'logs': [{
            'id': log.id,
            'plate_number': log.plate_number,
            'timestamp': log.timestamp.isoformat(),
            'authorized': log.authorized,
            'confidence': log.confidence,
            'user_name': log.user.full_name if log.user else None,
            'occupation': log.user.occupation if log.user else None,
            'image_path': log.image_path
        } for log in logs.items],
        'total': logs.total,
        'pages': logs.pages,
        'current_page': page
    })

@app.route('/api/reports/weekly')
@require_role(['admin'])
def weekly_report():
    """Generar reporte semanal"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    logs = AccessLog.query.filter(AccessLog.timestamp >= start_date, AccessLog.timestamp <= end_date).all()
    
    authorized_count = sum(1 for log in logs if log.authorized)
    denied_count = len(logs) - authorized_count
    
    occupation_stats = {}
    for log in logs:
        if log.user and log.authorized:
            occupation = log.user.occupation
            occupation_stats[occupation] = occupation_stats.get(occupation, 0) + 1
    
    hourly_stats = {}
    for log in logs:
        hour = log.timestamp.hour
        hourly_stats[hour] = hourly_stats.get(hour, 0) + 1
    
    return jsonify({
        'period': f"{start_date.date()} - {end_date.date()}",
        'authorized_accesses': authorized_count,
        'denied_accesses': denied_count,
        'occupation_distribution': occupation_stats,
        'peak_hours': sorted(hourly_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    })


# --- Bloque de ejecución principal ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                full_name='Administrador',
                occupation='admin',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
