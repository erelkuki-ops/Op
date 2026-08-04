# =============================================================
#  Asset Management - PT. Waskita Niagaprima (Streamlit)
#  Cara pakai:
#    1. Simpan kode ini sebagai streamlit_app.py
#    2. Taruh file logo.png di folder yang SAMA
#    3. (Opsional) requirements.txt akan dibuat otomatis
#    4. Jalankan: streamlit run streamlit_app.py
# =============================================================
import base64
import hashlib
import io
import sqlite3
import os
from datetime import date

import numpy as np
import pandas as pd
import qrcode
import streamlit as st
from PIL import Image

RED = "#C8102E"
DB_FILE = "assets.db"
LOGO_FILE = "logo.png"

# ============== AUTO-FIX LOGO TRANSPARAN (DIGABUNG) ==============
def fix_logo_transparency():
    if not os.path.isfile(LOGO_FILE):
        return
    try:
        img = Image.open(LOGO_FILE).convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        img.save(LOGO_FILE)
        print("Logo sudah transparan!")
    except Exception as e:
        print("Gagal proses logo:", e)

fix_logo_transparency()
# ===============================================================

# Auto-buat requirements.txt kalau belum ada
REQ_CONTENT = """streamlit
pandas
numpy
Pillow
qrcode
opencv-python-headless"""
if not os.path.exists("requirements.txt"):
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(REQ_CONTENT)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

st.set_page_config(page_title="Asset Management - PT. Waskita Niagaprima",
                   page_icon="🏗️", layout="wide")

# =============================================================
#  SEMBUNYIKAN ICON STREAMLIT CLOUD
#  (Share, star, pencil, GitHub, titik tiga, Manage app, dll)
#  >> Satu-satunya bagian yang DITAMBAHKAN, fitur lain utuh <<
# =============================================================
st.markdown("""
<style>
    /* Toolbar kanan atas: Share, star, pencil, GitHub, titik tiga */
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stToolbarActions"] { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    .stAppToolbar { display: none !important; }

    /* Tombol Deploy */
    [data-testid="stDeployButton"] { display: none !important; }
    .stAppDeployButton { display: none !important; }

    /* Tombol "Manage app" + status widget kanan bawah */
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="manage-app-button"] { display: none !important; }
    .stStatusWidget { display: none !important; }

    /* Garis pelangi atas, hamburger menu, header & footer bawaan */
    [data-testid="stDecoration"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .stAppHeader { display: none !important; }
    footer { display: none !important; }

    /* Rapikan jarak atas konten setelah header disembunyikan */
    .stMainBlockContainer,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)
# =============================================================

RED = "#C8102E"
DB_FILE = "assets.db"
LOGO_FILE = "logo.png"

# ---------- KREDENSIAL ----------
CREDS = {
    "admin":  {"hash": "b33a9061642a0f6e575d7e80880df613c1bae9ca644490be123ace353fec7650", "role": "admin"},
    "public": {"hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3", "role": "public"},
}

COLUMNS = [
    ("asset_id", "Asset ID"), ("asset_name", "Asset Name"), ("brand", "Brand"),
    ("model_type", "Model/Type"), ("serial_number", "Serial Number"),
    ("category", "Category"), ("sub_category", "Sub Category"), ("item_type", "Item Type"),
    ("qty", "Qty"), ("uom", "UOM"), ("condition", "Condition"),
    ("current_status", "Current Status"), ("current_project", "Current Project"),
    ("current_area", "Current Area"), ("current_location", "Current Location"),
    ("storage_type", "Storage Type"), ("cabinet_rack", "Cabinet/Rack"),
    ("shelf", "Shelf"), ("bin", "Bin"), ("purchase_date", "Purchase Date"),
    ("supplier", "Supplier"), ("po_number", "PO Number"),
    ("purchase_price", "Purchase Price"), ("remark", "Remark"),
]
COL_KEYS = [c[0] for c in COLUMNS]

CATEGORY_OPTIONS = ["Electrical Tools", "Mechanical Tools", "Hand Tools",
    "Measuring & Test Instruments", "Lifting Equipment", "Welding Equipment",
    "Power Equipment", "Personal Protective Equipment", "Vehicle",
    "Office Equipment", "IT Equipment", "Furniture", "Warehouse Equipment",
    "Civil Equipment", "Safety Equipment", "Consumable", "Spare Part"]

ITEM_TYPE_OPTIONS = ["Individual", "Group", "Tool Set Consumable"]
CURRENT_STATUS_OPTIONS = ["Available", "Reserved", "In Transit", "On Project",
    "Under Maintenance", "Under Calibration", "Lost", "Disposed"]
STORAGE_TYPE_OPTIONS = ["Warehouse", "Container", "Tool Box", "Cabinet", "Rack",
    "Shelf", "Bin", "Vehicle", "Office", "Site", "Workshop", "Consigned", "Personal Issue"]
SUB_CATEGORY_SUGGEST = ["Drill", "Grinder", "Cutting Machine", "Compressor", "Pump",
    "Wrench Set", "Screwdriver Set", "Hammer", "Multimeter", "Clamp Meter",
    "Insulation Tester", "Theodolite", "Total Station", "Chain Block", "Lever Hoist",
    "Sling", "Welding Machine", "Welding Torch", "Generator", "UPS", "Helmet",
    "Safety Shoes", "Safety Harness", "Truck", "Pickup", "Printer", "Scanner",
    "Laptop", "Desktop", "Monitor", "Router", "Desk", "Chair", "Pallet Jack",
    "Forklift", "Scaffolding", "Concrete Mixer", "Fire Extinguisher", "Gas Detector",
    "Consumable Material", "Spare Part Mechanical", "Spare Part Electrical"]


# ================= DATABASE =================
def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_conn()
    cols_sql = ", ".join(f"{k} TEXT" for k in COL_KEYS if k != "asset_id")
    conn.execute(f"CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, {cols_sql}, image_data TEXT)")
    conn.commit()
    conn.close()

def df_all(q=""):
    conn = get_conn()
    if q:
        like = f"%{q}%"
        df = pd.read_sql("""SELECT * FROM assets WHERE asset_id LIKE ? OR asset_name LIKE ?
               OR serial_number LIKE ? OR brand LIKE ? OR current_project LIKE ?
               OR current_location LIKE ? OR category LIKE ?""", conn, params=[like]*7)
    else:
        df = pd.read_sql("SELECT * FROM assets", conn)
    conn.close()
    return df

def upsert_asset(data: dict):
    conn = get_conn()
    keys = COL_KEYS + ["image_data"]
    vals = [str(data.get(k, "") or "") for k in keys]
    ph = ",".join("?" * len(keys))
    conn.execute(f"INSERT OR REPLACE INTO assets ({','.join(keys)}) VALUES ({ph})", vals)
    conn.commit()
    conn.close()

def delete_asset(aid):
    conn = get_conn()
    conn.execute("DELETE FROM assets WHERE asset_id = ?", (aid,))
    conn.commit()
    conn.close()

def delete_all():
    conn = get_conn()
    conn.execute("DELETE FROM assets")
    conn.commit()
    conn.close()

def asset_exists(aid):
    conn = get_conn()
    r = conn.execute("SELECT 1 FROM assets WHERE asset_id = ?", (aid,)).fetchone()
    conn.close()
    return r is not None

init_db()

# ================= HELPERS =================
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def img_to_b64(file_or_bytes, max_size=900) -> str:
    img = Image.open(file_or_bytes).convert("RGB")
    img.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def b64_to_img(b64str):
    if not b64str:
        return None
    raw = base64.b64decode(b64str.split(",", 1)[-1])
    return Image.open(io.BytesIO(raw))

def make_qr_png(text: str) -> bytes:
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def scan_qr_from_image(uploaded) -> str:
    if not HAS_CV2:
        return ""
    img = Image.open(uploaded).convert("RGB")
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(arr)
    return (data or "").strip()

# HANYA PAKAI logo.png — TIDAK ADA SVG FALLBACK
def logo(size=32):
    text_html = (
        f"""<div>
        <div style="font-family:Georgia,serif;font-weight:700;color:{RED};font-size:{size}px;line-height:1.1">Asset Management</div>
        <div style="font-family:Georgia,serif;font-weight:700;color:{RED};font-size:{int(size*0.45)}px;letter-spacing:.12em">PT. WASKITA NIAGAPRIMA</div>
        </div>""")
    if not os.path.exists(LOGO_FILE):
        st.error(f"File {LOGO_FILE} tidak ditemukan! Taruh logo.png di folder yang sama dengan streamlit_app.py")
        st.markdown(text_html, unsafe_allow_html=True)
        return
    with open(LOGO_FILE, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:12px">
        <img src="data:image/png;base64,{b64}" style="width:{int(size*2.8)}px" alt="Logo">
        {text_html}</div>""",
        unsafe_allow_html=True)

# ================= FORM INPUT ASET =================
def asset_form(existing: dict | None, form_key: str):
    e = existing or {}
    with st.form(form_key):
        c1, c2, c3 = st.columns(3)
        with c1:
            aid = st.text_input("Asset ID *", value=e.get("asset_id", ""), disabled=bool(existing))
            name = st.text_input("Asset Name *", value=e.get("asset_name", ""))
            brand = st.text_input("Brand", value=e.get("brand", ""))
            model = st.text_input("Model/Type", value=e.get("model_type", ""))
            serial = st.text_input("Serial Number", value=e.get("serial_number", ""))
            cat = st.selectbox("Category", [""] + CATEGORY_OPTIONS,
                index=([""] + CATEGORY_OPTIONS).index(e.get("category", "")) if e.get("category", "") in CATEGORY_OPTIONS else 0)
            subcat = st.selectbox("Sub Category (pilih / ketik di bawah)",
                [""] + SUB_CATEGORY_SUGGEST,
                index=([""] + SUB_CATEGORY_SUGGEST).index(e.get("sub_category", "")) if e.get("sub_category", "") in SUB_CATEGORY_SUGGEST else 0)
            subcat_manual = st.text_input("Sub Category (manual)", value="" if e.get("sub_category", "") in SUB_CATEGORY_SUGGEST else e.get("sub_category", ""))
        with c2:
            itype = st.selectbox("Item Type", [""] + ITEM_TYPE_OPTIONS,
                index=([""] + ITEM_TYPE_OPTIONS).index(e.get("item_type", "")) if e.get("item_type", "") in ITEM_TYPE_OPTIONS else 0)
            qty = st.text_input("Qty", value=e.get("qty", "1"))
            uom = st.text_input("UOM", value=e.get("uom", ""))
            cond = st.text_input("Condition", value=e.get("condition", "Baik"))
            status = st.selectbox("Current Status", [""] + CURRENT_STATUS_OPTIONS,
                index=([""] + CURRENT_STATUS_OPTIONS).index(e.get("current_status", "Available")) if e.get("current_status", "Available") in CURRENT_STATUS_OPTIONS else 0)
            proj = st.text_input("Current Project", value=e.get("current_project", ""))
            area = st.text_input("Current Area", value=e.get("current_area", ""))
            loc = st.text_input("Current Location", value=e.get("current_location", ""))
        with c3:
            stype = st.selectbox("Storage Type", [""] + STORAGE_TYPE_OPTIONS,
                index=([""] + STORAGE_TYPE_OPTIONS).index(e.get("storage_type", "")) if e.get("storage_type", "") in STORAGE_TYPE_OPTIONS else 0)
            crack = st.text_input("Cabinet/Rack", value=e.get("cabinet_rack", ""))
            shelf = st.text_input("Shelf", value=e.get("shelf", ""))
            bin_ = st.text_input("Bin", value=e.get("bin", ""))
            try:
                pdate_default = date.fromisoformat(e.get("purchase_date", "")) if e.get("purchase_date") else date.today()
            except ValueError:
                pdate_default = date.today()
            pdate = st.date_input("Purchase Date", value=pdate_default)
            supp = st.text_input("Supplier", value=e.get("supplier", ""))
            po = st.text_input("PO Number", value=e.get("po_number", ""))
            price = st.text_input("Purchase Price", value=e.get("purchase_price", ""))
        remark = st.text_area("Remark", value=e.get("remark", ""), height=70)
        st.markdown("**Foto Aset** — upload file foto (dari galeri atau kamera HP):")
        up_photo = st.file_uploader("📁 Upload Foto", type=["jpg", "jpeg", "png"], key=form_key + "_up")
        submitted = st.form_submit_button("💾 Simpan", type="primary")

    if submitted:
        aid_final = e.get("asset_id") if existing else aid.strip()
        if not aid_final or not name.strip():
            st.error("Asset ID dan Asset Name wajib diisi")
            return False
        if not existing and asset_exists(aid_final):
            st.error(f"Asset ID {aid_final} sudah ada")
            return False
        image_data = e.get("image_data", "")
        if up_photo is not None:
            image_data = img_to_b64(up_photo)
        upsert_asset({
            "asset_id": aid_final, "asset_name": name.strip(), "brand": brand,
            "model_type": model, "serial_number": serial, "category": cat,
            "sub_category": subcat_manual.strip() or subcat, "item_type": itype,
            "qty": qty or "1", "uom": uom, "condition": cond,
            "current_status": status, "current_project": proj,
            "current_area": area, "current_location": loc, "storage_type": stype,
            "cabinet_rack": crack, "shelf": shelf, "bin": bin_,
            "purchase_date": pdate.strftime("%Y-%m-%d"), "supplier": supp,
            "po_number": po, "purchase_price": price, "remark": remark,
            "image_data": image_data,
        })
        st.success("Aset diperbarui" if existing else "Aset ditambahkan")
        return True
    return False

def show_qr_block(aid: str, key_prefix: str = ""):
    png = make_qr_png(aid)
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(png, width=170, caption=f"QR — {aid}")
    with c2:
        st.download_button("⬇️ Download QR", data=png, file_name=f"qr-{aid}.png", mime="image/png", key=f"dlqr_{key_prefix}_{aid}")

def asset_card(row, is_admin, key_prefix):
    aid = row["asset_id"]
    with st.container(border=True):
        cimg, cinfo = st.columns([1, 4])
        with cimg:
            img = b64_to_img(row.get("image_data", ""))
            if img:
                st.image(img, width=110)
            else:
                st.markdown("<div style='font-size:44px;text-align:center'>🖼️</div>", unsafe_allow_html=True)
        with cinfo:
            st.markdown(f"<span style='color:{RED};font-weight:700;font-size:12px'>{aid}</span>", unsafe_allow_html=True)
            st.markdown(f"**{row['asset_name']}**  \n" +
                        f"{' · '.join(x for x in [row.get('brand',''), row.get('model_type',''), row.get('serial_number','')] if x) or '—'}")
            st.markdown(f"Status: **{row.get('current_status','-') or '-'}** | Qty: {row.get('qty','1')} {row.get('uom','')} | Category: {row.get('category','-') or '-'}")
            lokasi = " / ".join(x for x in [row.get("current_area",""), row.get("current_location",""),
                                            row.get("storage_type",""), row.get("cabinet_rack",""),
                                            row.get("shelf",""), row.get("bin","")] if x) or "-"
            st.markdown(f"Lokasi: {lokasi}  \nRemark: {row.get('remark','-') or '-'}")

        n_btn = 4 if is_admin else 1
        bcols = st.columns(n_btn)
        if bcols[0].button("🔖 QR", key=f"{key_prefix}_qr_{aid}"):
            st.session_state["show_qr_for"] = aid
        if is_admin:
            if bcols[1].button("✏️ Update", key=f"{key_prefix}_upd_{aid}"):
                st.session_state["edit_id"] = aid
            if bcols[2].button("🚚 Moving", key=f"{key_prefix}_mov_{aid}"):
                st.session_state["move_id"] = aid
            if bcols[3].button("🗑️ Delete", key=f"{key_prefix}_del_{aid}"):
                delete_asset(aid)
                st.rerun()

        if st.session_state.get("show_qr_for") == aid:
            show_qr_block(aid, key_prefix)

        if is_admin and st.session_state.get("edit_id") == aid:
            st.markdown("---")
            if asset_form(dict(row), f"edit_{key_prefix}_{aid}"):
                st.session_state.pop("edit_id", None)
                st.rerun()

        if is_admin and st.session_state.get("move_id") == aid:
            st.markdown("---")
            st.markdown(f"**🚚 Moving Aset — {aid}**")
            with st.form(f"move_{key_prefix}_{aid}"):
                m1, m2 = st.columns(2)
                with m1:
                    mstatus = st.selectbox("Status", [""] + CURRENT_STATUS_OPTIONS,
                        index=([""] + CURRENT_STATUS_OPTIONS).index(row.get("current_status", "")) if row.get("current_status", "") in CURRENT_STATUS_OPTIONS else 0, key=f"mv_status_{key_prefix}_{aid}")
                    mproj = st.text_input("Project", value=row.get("current_project", ""))
                    marea = st.text_input("Area", value=row.get("current_area", ""))
                    mloc = st.text_input("Location", value=row.get("current_location", ""))
                with m2:
                    mstype = st.selectbox("Storage Type", [""] + STORAGE_TYPE_OPTIONS,
                        index=([""] + STORAGE_TYPE_OPTIONS).index(row.get("storage_type", "")) if row.get("storage_type", "") in STORAGE_TYPE_OPTIONS else 0)
                    mcrack = st.text_input("Cabinet/Rack", value=row.get("cabinet_rack", ""))
                    mshelf = st.text_input("Shelf", value=row.get("shelf", ""))
                    mbin = st.text_input("Bin", value=row.get("bin", ""))
                mremark = st.text_area("Remark", value=row.get("remark", ""), height=60)
                if st.form_submit_button("💾 Simpan Moving", type="primary"):
                    d = dict(row)
                    d.update({"current_status": mstatus, "current_project": mproj,
                              "current_area": marea, "current_location": mloc,
                              "storage_type": mstype, "cabinet_rack": mcrack,
                              "shelf": mshelf, "bin": mbin, "remark": mremark})
                    upsert_asset(d)
                    st.session_state.pop("move_id", None)
                    st.success("Lokasi/status aset diperbarui")
                    st.rerun()

# ================= LOGIN =================
if "role" not in st.session_state:
    st.session_state["role"] = None

if not st.session_state["role"]:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        logo(26)
        st.info("Kelola inventaris aset, upload database CSV, scan & cari aset, foto aset, update lokasi, serta generate QR code.")
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary", use_container_width=True):
                cred = CREDS.get(u.strip().lower())
                if cred and cred["hash"] == sha256(p):
                    st.session_state["role"] = cred["role"]
                    st.rerun()
                else:
                    st.error("Username atau password salah")
        st.caption("Admin: kelola data · Public: lihat & scan")
    st.stop()

role = st.session_state["role"]
is_admin = role == "admin"

# ================= HEADER =================
h1, h2 = st.columns([3, 1])
with h1:
    logo(22)
with h2:
    total = len(df_all())
    st.markdown(
        f"<div style='text-align:right'>"
        f"<span style='background:{'#C8102E' if is_admin else '#e2e8f0'};color:{'#fff' if is_admin else '#334155'};"
        f"border-radius:999px;padding:4px 12px;font-size:12px;font-weight:600'>"
        f"{'👑 Admin' if is_admin else '👁️ Public (lihat & scan)'}</span> "
        f"<span style='background:#fef2f2;color:{RED};border-radius:999px;padding:4px 12px;"
        f"font-size:12px;font-weight:600'>{total} aset</span></div>",
        unsafe_allow_html=True)
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

st.markdown("---")

# ================= TABS =================
if is_admin:
    tab1, tab2, tab3 = st.tabs(["🏠 List Aset", "📤 Upload Database", "📷 Scan & Search"])
else:
    tab1, tab3 = st.tabs(["🏠 List Aset", "📷 Scan & Search"])
    tab2 = None

# ---------- TAB 1 : LIST ASET ----------
with tab1:
    tc1, tc2 = st.columns([3, 1])
    with tc1:
        flt = st.text_input("Filter di list (ID, nama, serial...)", key="list_filter")
    with tc2:
        st.write("")
        if is_admin and st.button("➕ Tambah Aset", type="primary"):
            st.session_state["show_input"] = not st.session_state.get("show_input", False)

    if is_admin and st.session_state.get("show_input"):
        st.subheader("Input Aset Baru")
        if asset_form(None, "form_new"):
            st.session_state["show_input"] = False
            st.rerun()

    df = df_all(flt)
    if df.empty:
        st.info("Belum ada data aset. Tambah manual atau upload CSV di tab Upload Database.")
    else:
        show = df.copy()
        show.insert(1, "Foto", show["image_data"].apply(lambda x: "📷" if x else ""))
        show = show[["asset_id", "Foto"] + COL_KEYS[1:]]
        show.columns = ["Asset ID", "Foto"] + [c[1] for c in COLUMNS[1:]]
        st.dataframe(show, use_container_width=True, hide_index=True)

        st.download_button("⬇️ Export CSV",
                           data=df[COL_KEYS].to_csv(index=False).encode("utf-8"),
                           file_name="assets-export.csv", mime="text/csv")

        st.markdown("#### Detail / Aksi per Aset")
        pilih = st.selectbox("Pilih aset", [""] + df["asset_id"].tolist(), key="list_pick")
        if pilih:
            row = df[df["asset_id"] == pilih].iloc[0].to_dict()
            asset_card(row, is_admin, "list")

# ---------- TAB 2 : UPLOAD DATABASE (ADMIN) ----------
if tab2 is not None:
    with tab2:
        cu1, cu2 = st.columns([1.3, 1])
        with cu1:
            st.subheader("Upload Database Aset")
            st.caption("Urutan kolom CSV: " + ", ".join(c[1] for c in COLUMNS))
            up = st.file_uploader("File CSV / TSV", type=["csv", "tsv"])
            mode = st.selectbox("Mode Upload", [
                "Upsert — update jika ID sudah ada, insert jika baru",
                "Insert only — lewati ID yang sudah ada",
                "Replace all — hapus semua lalu isi dari file"])
            if st.button("📤 Upload Database", type="primary") and up:
                try:
                    sep = "\t" if up.name.endswith(".tsv") else ","
                    dfu = pd.read_csv(up, sep=sep, dtype=str).fillna("")
                    dfu.columns = [c.strip().lower().replace(" ", "_").replace("/", "_") for c in dfu.columns]
                    alias = {"assetid": "asset_id", "assetname": "asset_name",
                             "model_type": "model_type", "modeltype": "model_type"}
                    dfu.rename(columns=alias, inplace=True)
                    valid = dfu[(dfu.get("asset_id", "") != "") & (dfu.get("asset_name", "") != "")]
                    if valid.empty:
                        st.error("Tidak ada baris valid. Pastikan header memuat asset_id dan asset_name.")
                    else:
                        ins = updt = skip = 0
                        if mode.startswith("Replace"):
                            delete_all()
                        for _, r in valid.iterrows():
                            d = {k: str(r.get(k, "") or "") for k in COL_KEYS}
                            exists = asset_exists(d["asset_id"])
                            if exists and mode.startswith("Insert"):
                                skip += 1
                                continue
                            if exists:
                                updt += 1
                            else:
                                ins += 1
                            upsert_asset(d)
                        st.success(f"Upload berhasil — {ins} baru, {updt} diupdate, {skip} dilewati")
                        st.rerun()
                except Exception as ex:
                    st.error(f"Gagal memproses file: {ex}")
        with cu2:
            st.subheader("Template CSV")
            tpl = ",".join(COL_KEYS) + "\nAST-001,Laptop Dell Latitude,Dell,Latitude 5440,SN123,IT Equipment,Laptop,Individual,1,unit,Baik,Available,HQ,Lantai 2,Gudang A,Warehouse,R1,S2,B1,2024-01-15,Supplier A,PO-001,12500000,Contoh data"
            st.code(",".join(COL_KEYS), language="text")
            st.download_button("⬇️ Download Template", data=tpl.encode(),
                               file_name="template-assets.csv", mime="text/csv")
            st.markdown("---")
            st.subheader("⚠️ Zona Bahaya")
            if st.button("🗑️ Hapus Semua Data"):
                st.session_state["confirm_wipe"] = True
            if st.session_state.get("confirm_wipe"):
                st.warning("Yakin hapus SEMUA data aset? Tidak bisa dibatalkan.")
                cw1, cw2 = st.columns(2)
                if cw1.button("Ya, hapus semua", type="primary"):
                    delete_all()
                    st.session_state.pop("confirm_wipe", None)
                    st.rerun()
                if cw2.button("Batal"):
                    st.session_state.pop("confirm_wipe", None)
                    st.rerun()

# ---------- TAB 3 : SCAN & SEARCH ----------
with tab3:
    st.subheader("Scan & Search")
    st.caption("Scan QR code aset langsung dengan kamera, atau cari berdasarkan Asset ID, nama, serial number, brand, project, atau lokasi.")

    sc1, sc2 = st.columns([2, 1])
    with sc1:
        q = st.text_input("Scan / ketik Asset ID atau nama...", key="scan_q")
    with sc2:
        with st.expander("📷 Scan QR"):
            if not HAS_CV2:
                st.warning("Install opencv-python-headless untuk fitur scan QR:\n`pip install opencv-python-headless`")
            qr_file = st.file_uploader("📁 Upload foto QR code", type=["jpg", "jpeg", "png"], key="qr_upload")
            shot = st.camera_input("Atau jepret QR dengan kamera", key="qr_cam")
            target = qr_file or shot
            if target is not None and HAS_CV2:
                decoded = scan_qr_from_image(target)
                if decoded:
                    st.success(f"QR terbaca: {decoded}")
                    q = decoded
                else:
                    st.error("QR tidak terbaca. Coba lebih dekat / lebih terang.")

    dfs = df_all(q) if q else df_all()
    if dfs.empty:
        st.info("Tidak ada hasil. Coba kata kunci lain atau upload database dulu.")
    else:
        for _, row in dfs.iterrows():
            asset_card(row.to_dict(), is_admin, "scan")