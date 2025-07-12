
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template
import os
import pdfplumber
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import re
import sqlite3
from flask_cors import CORS
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Union

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = 'contratos.db'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contratos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_archivo TEXT,
                cliente TEXT,
                monto_total REAL,
                fecha_inicio TEXT,
                frecuencia TEXT,
                duracion_meses INTEGER,
                fecha_procesamiento TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contrato_id INTEGER,
                numero_pago INTEGER,
                fecha TEXT,
                monto REAL,
                estado TEXT DEFAULT 'pendiente',
                FOREIGN KEY (contrato_id) REFERENCES contratos(id)
            )
        """)
        conn.commit()

@app.before_request
def before_request_func():
    init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

@app.route('/')
def home():
    return "Servidor CPA Forecast activo"
    
    
@app.route('/dashboard')
def dashboard():
    return render_template('index.html')
    
    

@app.route('/api/upload', methods=['POST'])
def upload_pdfs():
    if 'pdfs' not in request.files:
        return jsonify({'success': False, 'error': 'No se enviaron archivos PDF'}), 400

    archivos = request.files.getlist('pdfs')
    resultados = []

    for file in archivos:
        if not allowed_file(file.filename):
            resultados.append({'archivo': file.filename, 'error': 'Tipo de archivo no permitido'})
            continue

        if file.content_length and file.content_length > MAX_FILE_SIZE:
            resultados.append({'archivo': file.filename, 'error': 'Archivo demasiado grande (máx 10MB)'})
            continue

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        try:
            file.save(filepath)
            resultado = extract_info_from_pdf(filepath)
            resultado['archivo'] = file.filename

            if all(k in resultado for k in ['inicio', 'monto', 'frecuencia', 'duracion_meses']) and isinstance(resultado.get('pagos'), list):
                save_to_database(resultado)
            resultados.append(resultado)
        except Exception as e:
            resultados.append({'archivo': file.filename, 'error': f'Error al procesar el archivo: {str(e)}'})
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({'success': True, 'data': resultados})

def extract_info_from_pdf(pdf_path: str) -> Dict[str, Union[str, float]]:
    try:
        text_content = ''
        with pdfplumber.open(pdf_path) as pdf:
            text_content = ''.join(page.extract_text() or '' for page in pdf.pages)

        if not text_content.strip():
            text_content = ''
            doc = fitz.open(pdf_path)
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text_content += pytesseract.image_to_string(img, lang='spa')
            doc.close()

        if not text_content.strip():
            return {'error': 'El PDF no contiene texto legible (ni extraíble ni por OCR)'}

        full_text_lower = text_content.lower()

        cliente = re.search(r'cliente.*?por\s+([^,]+)', text_content, re.IGNORECASE)
        monto = re.search(r'(?:cantidad total de|monto|importe).*?\$?\s*([\d,.]+)', full_text_lower)
        fecha_inicio = re.search(r'(?:a partir del|vigencia).*?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})', full_text_lower)
        frecuencia = re.search(r'(mensual|bimestral|trimestral|semestral|anual)', full_text_lower)
        duracion = re.search(r'vigencia\s+de\s+(\d+)\s+mes', full_text_lower)

        inicio = fecha_inicio.group(1).title() if fecha_inicio else 'No especificado'
        monto_val = float(monto.group(1).replace(',', '').replace('$', '')) if monto else 0.0
        frecuencia_val = frecuencia.group(1).capitalize() if frecuencia else 'Mensual'
        duracion_val = int(duracion.group(1)) if duracion else 12

        pagos = generar_plan_de_pagos(inicio, monto_val, frecuencia_val, duracion_val)

        return {
            'cliente': cliente.group(1).strip() if cliente else 'No especificado',
            'monto': monto_val,
            'inicio': inicio,
            'frecuencia': frecuencia_val,
            'duracion_meses': duracion_val,
            'pagos': pagos
        }
    except Exception as e:
        return {'error': str(e)}

def generar_plan_de_pagos(fecha_inicio_str: str, monto_total: Union[str, float], frecuencia: str, meses: Union[str, int]) -> List[Dict[str, Union[str, float]]]:
    meses_es = {
        'enero': 'January', 'febrero': 'February', 'marzo': 'March', 'abril': 'April',
        'mayo': 'May', 'junio': 'June', 'julio': 'July', 'agosto': 'August',
        'septiembre': 'September', 'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December'
    }
    fecha_normalizada = fecha_inicio_str.lower()
    for es, en in meses_es.items():
        fecha_normalizada = fecha_normalizada.replace(es, en.lower())

    fecha_inicio = datetime.strptime(fecha_normalizada, '%d de %B de %Y')
    frecuencia_meses = {'Mensual': 1, 'Bimestral': 2, 'Trimestral': 3, 'Semestral': 6, 'Anual': 12}.get(frecuencia, 1)

    meses = int(meses)
    monto_total = float(monto_total)
    total_pagos = max(1, meses // frecuencia_meses)
    monto_por_pago = round(monto_total / total_pagos, 2)

    return [
        {
            'numero_pago': i + 1,
            'fecha': (fecha_inicio + relativedelta(months=i * frecuencia_meses)).strftime('%d/%m/%Y'),
            'monto': monto_por_pago
        }
        for i in range(total_pagos)
    ]

def save_to_database(contrato: Dict):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO contratos (nombre_archivo, cliente, monto_total, fecha_inicio, frecuencia, duracion_meses)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            contrato['archivo'],
            contrato['cliente'],
            contrato['monto'],
            contrato['inicio'],
            contrato['frecuencia'],
            contrato['duracion_meses']
        ))
        contrato_id = cursor.lastrowid

        for pago in contrato.get('pagos', []):
            cursor.execute("""
                INSERT INTO pagos (contrato_id, numero_pago, fecha, monto)
                VALUES (?, ?, ?, ?)
            """, (
                contrato_id,
                pago['numero_pago'],
                pago['fecha'],
                pago['monto']
            ))
        conn.commit()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 5000
    app.run(host='0.0.0.0', port=port, debug=True)