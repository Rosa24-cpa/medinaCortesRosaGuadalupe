# CPA Forecast - Hackatón CPA Vision 2025

**Autor(a):** Rosa Guadalupe Medina Cortés  
**Repositorio:** [GitHub - medinaCortesRosaGuadalupe](https://github.com/Rosa24-cpa/medinaCortesRosaGuadalupe)  
**Rama:** `medinaCortesRosaGuadalupe`  
**Fecha de entrega:** 12/07/2025

## 🚀 Descripción General

**CPA Forecast** es un sistema inteligente de pronóstico de cobranza que automatiza la lectura de contratos PDF (incluso escaneados), extrae los datos clave mediante técnicas de inteligencia artificial (incluyendo OCR), genera un plan de cobranza detallado y presenta una visualización clara de los pagos futuros y los ingresos devengados a lo largo del tiempo.

Este sistema fue desarrollado como solución al reto del **Hackatón CPA Vision 2025**.

---

## ✅ Funcionalidades Principales

- 📤 Carga de contratos en PDF
- 🧠 Análisis del contrato mediante procesamiento de texto y OCR
- 📅 Generación automática de plan de pagos
- 📊 Visualización:
  - Línea de tiempo de pagos futuros
  - Gráfica de ingresos devengados
- 🗃️ Persistencia de la información en base de datos SQLite
- 🌐 Interfaz Web amigable

---

## 🧠 Inteligencia Artificial Aplicada

- Utiliza `pdfplumber` para extraer texto de PDFs digitales.
- Integra `Tesseract OCR` para leer texto de contratos escaneados.
- Analiza el contenido textual y reconoce expresiones comunes para:
  - Cliente
  - Monto total
  - Fecha de inicio
  - Frecuencia de pago
  - Duración

---

## ⚙️ Tecnologías Utilizadas

- Python + Flask
- SQLite
- pdfplumber + pytesseract + PyMuPDF
- HTML + CSS + Bootstrap
- Chart.js

---

## 📁 Estructura del Proyecto

- `app.py` – API principal en Flask
- `contratos.db` – Base de datos local SQLite
- `templates/` – HTML del dashboard
- `static/` – Archivos JS y CSS
- `uploads/` – Carpeta temporal para PDFs
- `requirements.txt` – Lista de dependencias

---

## 🚨 Consideraciones

- Los contratos escaneados deben tener texto claro y legible para que el OCR funcione correctamente.
- Asegúrate de tener `spa.traineddata` instalado para el OCR en español.
- El sistema está configurado para ejecución local en entorno de desarrollo (`debug=True`).

---

## 🧾 Memoria Técnica (resumen)

Se eligió Flask por su ligereza y rapidez de desarrollo. Para la extracción de datos se combinaron técnicas de procesamiento de texto y OCR para dar soporte a contratos tanto digitales como escaneados. La interfaz está pensada para mostrar de forma clara los KPIs que buscan automatizar la cobranza. Toda la información se almacena en una base SQLite de forma persistente y reutilizable.

---

## 🧪 Para ejecutar localmente

```bash
git clone https://github.com/Rosa24-cpa/medinaCortesRosaGuadalupe.git
cd medinaCortesRosaGuadalupe
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
python app.py
```

---

¡Gracias por revisar el proyecto!

