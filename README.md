# AUP Hash App — UI+ (Streamlit)

UI mejorada para:
- Calcular hashes (SHA-256/512, BLAKE2b, etc.).
- Generar **Acta de Integridad** (DOCX) en memoria y descargarla de inmediato.
- Guardar todo en **SQLite** con opción de detectar duplicados por SHA-256.
- **Verificar** archivo contra hash esperado.
- Consultar bitácora y descargar Actas por ID.

## Uso rápido
```bash
pip install -r requirements.txt
streamlit run app.py
```