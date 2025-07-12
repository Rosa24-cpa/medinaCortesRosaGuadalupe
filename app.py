# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import os
import pdfplumber
import re
import sqlite3
from flask_cors import CORS
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Union, Dict

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
DATABASE = 'cpa_forecast.db'

@app.route('/')
def home():
    return "Servidor Flask activo!"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}

@app.route('/api/upload', methods=['POST'])
def upload_pdfs():
    if 'pdfs' not in request.files:
        return jsonify({'success': False, 'error': 'No se enviaron archivos PDF'}), 400

    archivos = request.files.getlist('pdfs')
    if not archivos or all(file.filename == '' for file in archivos):
        return jsonify({'success': False, 'error': 'No se seleccionaron archivos'}), 400

    resultados = []

    for file in archivos:
        if not allowed_file(file.filename):
            resultados.append({'archivo': file.filename, 'error': 'Tipo de archivo no permitido'})
            continue

        if file.content_length and file.content_length > MAX_FILE_SIZE:
            resultados.append({'archivo': file.filename, 'error': 'Archivo demasiado grande (max 10MB)'})
            continue

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        try:
            file.save(filepath)

            resultado = extract_info_from_pdf(filepath)
            resultado['archivo'] = file.filename

            if all(key in resultado for key in ['inicio', 'monto', 'frecuencia', 'duracion_meses']):
                resultado['pagos'] = generar_plan_de_pagos(
                    resultado['inicio'],
                    resultado['monto'],
                    resultado['frecuencia'],
                    resultado['duracion_meses']
                )
                save_to_database(resultado)

            resultados.append(resultado)

        except Exception as e:
            resultados.append({'archivo': file.filename, 'error': f'Error al procesar el archivo: {str(e)}'})
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({
        'success': True,
        'data': resultados,
        'message': f'Se procesaron {len(resultados)} archivos'
    })

def extract_info_from_pdf(pdf_path: str) -> Dict[str, Union[str, float]]:
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ''.join(page.extract_text() or '' for page in pdf.pages)

        if not full_text.strip():
            return {'error': 'El PDF no contiene texto extraible'}

        full_text_lower = full_text.lower()

        cliente = re.search(r'cliente.*?por\s+([^,\n]+)', full_text, re.IGNORECASE)
        monto = re.search(r'(?:total\s+a\s+pagar|monto|importe).*?\$?\s*([\d,.]+)', full_text_lower)
        fecha_inicio = re.search(r'(?:inicio|vigencia|a\s+partir\s+del)\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})', full_text_lower)
        frecuencia = re.search(r'(?:frecuencia|periodicidad)\s+(mensual|bimestral|trimestral|semestral|anual)', full_text_lower)
        duracion = re.search(r'(?:duracion|vigencia)\s+(?:de\s+)?(\d+)\s+(?:meses|mes)', full_text_lower)

        return {
            'cliente': cliente.group(1).strip() if cliente else 'No especificado',
            'monto': float(monto.group(1).replace(',', '')) if monto else 0.0,
            'inicio': fecha_inicio.group(1).title() if fecha_inicio else 'No especificado',
            'frecuencia': frecuencia.group(1).capitalize() if frecuencia else 'Mensual',
            'duracion_meses': duracion.group(1) if duracion else '12'
        }

def generar_plan_de_pagos(
    fecha_inicio_str: str,
    monto_total: Union[str, float],
    frecuencia: str,
    meses: Union[str, int]
) -> List[Dict[str, Union[str, float]]]:
    try:
        meses = int(meses) if isinstance(meses, str) else meses
        monto_total = float(monto_total) if isinstance(monto_total, str) else monto_total

        if meses <= 0 or monto_total <= 0:
            return [{'error': 'Duracion o monto invalido'}]

        meses_espanol = {
            'enero': 'January', 'febrero': 'February', 'marzo': 'March',
            'abril': 'April', 'mayo': 'May', 'junio': 'June',
            'julio': 'July', 'agosto': 'August', 'septiembre': 'September',
            'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December'
        }

        fecha_normalizada = fecha_inicio_str.lower()
        for mes_es, mes_en in meses_espanol.items():
            fecha_normalizada = fecha_normalizada.replace(mes_es, mes_en.lower())

        fecha_inicio = datetime.strptime(fecha_normalizada, '%d de %B de %Y')

        frecuencia_meses = {
            'Mensual': 1, 'Bimestral': 2, 'Trimestral': 3,
            'Semestral': 6, 'Anual': 12
        }.get(frecuencia.capitalize(), 1)

        total_pagos = max(1, meses // frecuencia_meses)
        monto_por_pago = round(monto_total / total_pagos, 2)

        return [
            {
                'numero_pago': i + 1,
                'fecha': (fecha_inicio + relativedelta(months=i * frecuencia_meses)).strftime('%d/%m/%Y'),
                'monto': monto_por_pago,
                'frecuencia': frecuencia.capitalize()
            }
            for i in range(total_pagos)
        ]
    except Exception as e:
        return [{'error': str(e)}]

def save_to_database(contrato: Dict):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contratos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_archivo TEXT,
                cliente TEXT,
                monto_total REAL,
                fecha_inicio TEXT,
                frecuencia TEXT,
                duracion_meses INTEGER,
                fecha_procesamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contrato_id INTEGER,
                numero_pago INTEGER,
                fecha TEXT,
                monto REAL,
                estado TEXT DEFAULT 'pendiente',
                FOREIGN KEY (contrato_id) REFERENCES contratos(id)
            )
        ''')

        cursor.execute('''
            INSERT INTO contratos (
                nombre_archivo, cliente, monto_total,
                fecha_inicio, frecuencia, duracion_meses
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            contrato['archivo'],
            contrato['cliente'],
            float(contrato['monto']),
            contrato['inicio'],
            contrato['frecuencia'],
            int(contrato['duracion_meses'])
        ))

        contrato_id = cursor.lastrowid

        if 'pagos' in contrato and contrato['pagos']:
            for pago in contrato['pagos']:
                cursor.execute('''
                    INSERT INTO pagos (
                        contrato_id, numero_pago, fecha, monto
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    contrato_id,
                    pago['numero_pago'],
                    pago['fecha'],
                    float(pago['monto'])
                ))

        conn.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
