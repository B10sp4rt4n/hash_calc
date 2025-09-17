import streamlit as st
import hashlib, sqlite3, pandas as pd, datetime, io, os, mimetypes
from acta_helper import generar_acta_docx_bytes

st.set_page_config(page_title="AUP Hash App — UI+", page_icon="🧾", layout="centered")
st.title("🧾 AUP Hash App — UI+ (Integridad y Bitácora)")
st.caption("Calcula hashes, genera Actas de Integridad (DOCX) y guarda bitácora en SQLite, todo con una UI sencilla.")

DB_PATH = "hash_log.sqlite"

@st.cache_resource
def get_conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    return con

def ensure_schema():
    with open("schema.sql","r",encoding="utf-8") as s:
        schema = s.read()
    con = get_conn()
    cur = con.cursor()
    for stmt in schema.split(";"):
        if stmt.strip():
            cur.execute(stmt)
    con.commit()

def compute_hashes(file_bytes: bytes, algos: list[str]):
    results = {}
    for a in algos:
        h = hashlib.new(a)
        # chunking
        bio = io.BytesIO(file_bytes)
        for chunk in iter(lambda: bio.read(1024*1024), b""):
            h.update(chunk)
        results[a] = h.hexdigest()
    return results

ensure_schema()

tab1, tab2, tab3 = st.tabs(["🔐 Hashear & Acta", "✅ Verificar", "📚 Bitácora"])

with tab1:
    with st.sidebar:
        st.header("⚙️ Opciones")
        actor = st.text_input("Autor/Custodio", value="SRE")
        location = st.text_input("Lugar", value="Ciudad de México")
        doc_title = st.text_input("Título del documento", value="SEMILLA AUP — Obra Literaria Técnico‑Estructural")
        notes = st.text_area("Notas (opcional)", value="", height=80)
        st.markdown("---")
        st.markdown("**Algoritmos**")
        algos_sel = st.multiselect("Selecciona algoritmos", ["sha256","sha512","blake2b","sha1","md5"], default=["sha256","sha512","blake2b"])
        prev_hash = st.text_input("Hash previo (encadenamiento, opcional)", value="")

    st.subheader("1) Cargar archivo(s)")
    files = st.file_uploader("Arrastra o selecciona uno o varios archivos", type=None, accept_multiple_files=True)

    if files:
        rows = []
        # progress
        progress = st.progress(0, text="Calculando hashes...")
        for i, f in enumerate(files, start=1):
            b = f.read()
            hashes = compute_hashes(b, algos_sel or ["sha256"])
            size = len(b)
            mimetype = f.type or mimetypes.guess_type(f.name)[0] or ""
            row = {"filename": f.name, "size_bytes": size, "mimetype": mimetype}
            row.update({k:v for k,v in hashes.items()})
            rows.append(row)
            progress.progress(int(i/len(files)*100), text=f"Procesado {i}/{len(files)}")
        progress.empty()

        df = pd.DataFrame(rows)
        st.success("Hashes calculados.")
        st.dataframe(df, use_container_width=True)

        st.subheader("2) Generar Acta(s) y Guardar en Bitácora")
        if st.button("Guardar evento(s) y descargar Acta(s)"):
            con = get_conn()
            cur = con.cursor()
            created_at = datetime.datetime.utcnow().isoformat()

            for r in rows:
                # Detectar posible duplicado por SHA-256
                dupe = None
                if r.get("sha256"):
                    cur.execute("SELECT id, filename, created_at FROM hash_events WHERE sha256 = ? LIMIT 1", (r["sha256"],))
                    dupe = cur.fetchone()
                if dupe:
                    st.warning(f"Posible duplicado (SHA-256 ya registrado): ID={dupe[0]} archivo={dupe[1]} fecha={dupe[2]}")

                meta = {
                    "titulo_documento": doc_title,
                    "actor": actor,
                    "lugar": location,
                    "fecha_acta": datetime.date.today().isoformat(),
                    "nombre_archivo": r["filename"],
                    "tamano_bytes": r["size_bytes"],
                    "mimetype": r["mimetype"],
                    "notas": notes
                }
                enc = {"hash_previo": prev_hash} if prev_hash else None
                acta_name, acta_bytes = generar_acta_docx_bytes(meta, {k:v for k,v in r.items() if k in ['sha256','sha512','blake2b','sha1','md5']}, enc)

                cur.execute("""
                    INSERT INTO hash_events (
                        created_at, actor, location, doc_title, filename, size_bytes, mimetype,
                        algo_primary, sha256, sha512, blake2b, sha1, md5, notes, acta_blob, acta_filename
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    created_at, actor, location, doc_title, r["filename"], r["size_bytes"], r["mimetype"],
                    (algos_sel or ["sha256"])[0],
                    r.get("sha256"), r.get("sha512"), r.get("blake2b"), r.get("sha1"), r.get("md5"),
                    notes, acta_bytes, acta_name
                ))
                st.download_button(f"Descargar {acta_name}", data=acta_bytes, file_name=acta_name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

            con.commit()
            st.success("Evento(s) guardado(s) en bitácora.")

with tab2:
    st.subheader("Verificar hash vs archivo")
    expected = st.text_input("Pega el hash esperado (SHA‑256 u otro)", value="")
    vf = st.file_uploader("Sube el archivo a verificar", type=None, accept_multiple_files=False, key="verify_file")
    algo_v = st.selectbox("Algoritmo", ["sha256","sha512","blake2b","sha1","md5"], index=0)

    if st.button("Verificar") and vf and expected:
        b = vf.read()
        h = hashlib.new(algo_v)
        bio = io.BytesIO(b)
        for chunk in iter(lambda: bio.read(1024*1024), b""):
            h.update(chunk)
        got = h.hexdigest()
        if got.lower() == expected.strip().lower():
            st.success("✅ Coincide. El archivo es íntegro según el hash proporcionado.")
        else:
            st.error("❌ No coincide. El hash calculado es distinto.")
        st.code(got)

with tab3:
    st.subheader("Bitácora")
    con = get_conn()
    dfh = pd.read_sql_query("SELECT id, created_at, actor, location, doc_title, filename, size_bytes, algo_primary, sha256, sha512, blake2b, sha1, md5, acta_filename FROM hash_events ORDER BY id DESC", con)
    st.dataframe(dfh, use_container_width=True)

    st.markdown("**Descargar Acta por ID**")
    id_sel = st.number_input("ID", min_value=0, value=0, step=1)
    if st.button("Descargar Acta"):
        cur = con.cursor()
        cur.execute("SELECT acta_blob, acta_filename FROM hash_events WHERE id = ?", (int(id_sel),))
        row = cur.fetchone()
        if row and row[0]:
            st.download_button(row[1] or "Acta.docx", data=row[0], file_name=row[1] or "Acta.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.warning("No se encontró acta para ese ID.")