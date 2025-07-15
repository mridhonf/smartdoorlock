import streamlit as st
import time
import sqlite3
from datetime import datetime
import smtplib
from email.message import EmailMessage
import pandas as pd

# ======================== FUNGSI LOG & EMAIL ========================
def log_akses(status, keterangan):
    conn = sqlite3.connect('log_akses.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS log_akses 
                 (waktu TEXT, status TEXT, keterangan TEXT)''')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT INTO log_akses VALUES (?, ?, ?)", (now, status, keterangan))
    conn.commit()
    conn.close()

def kirim_email(subject, body):
    EMAIL_PENGIRIM = "emailkamu@gmail.com"
    PASSWORD = "app_password_gmail"

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_PENGIRIM
    msg["To"] = "emailtujuan@gmail.com"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_PENGIRIM, PASSWORD)
            smtp.send_message(msg)
    except:
        st.warning("📧 Gagal mengirim notifikasi email (cek pengaturan SMTP).")

# ======================== SETUP HALAMAN ========================
st.set_page_config(page_title="Smart Door Lock", page_icon="🔐")
st.title("🔐 Smart Door Lock System")

# Inisialisasi state
if 'pin_terdaftar' not in st.session_state:
    st.session_state.pin_terdaftar = "1234"
if 'percobaan' not in st.session_state:
    st.session_state.percobaan = 0
if 'terkunci' not in st.session_state:
    st.session_state.terkunci = False
if 'pintu_terbuka' not in st.session_state:
    st.session_state.pintu_terbuka = False
if 'security_mode' not in st.session_state:
    st.session_state.security_mode = False
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time.time()

pin_master = "0000"
max_attempt = 3
waktu_timeout = 10

# ======================== FUNGSI AUTO LOCK ========================
def check_auto_lock():
    if st.session_state.pintu_terbuka:
        now = time.time()
        if now - st.session_state.last_activity > waktu_timeout:
            st.session_state.pintu_terbuka = False
            st.success("🔒 Pintu terkunci otomatis karena tidak ada aktivitas.")
            log_akses("🔒 Otomatis Terkunci", "Timeout tidak ada aktivitas")

check_auto_lock()

# ======================== TOMBOL SECURITY MODE ========================
col1, col2 = st.columns(2)
with col1:
    if st.button("🛡️ Toggle Security Mode"):
        st.session_state.security_mode = not st.session_state.security_mode
        if st.session_state.security_mode:
            st.warning("🛡️ Security Mode AKTIF. Semua akses dibatasi.")
            log_akses("🛡️ Security Mode", "Aktifkan")
        else:
            st.success("✅ Security Mode DINONAKTIFKAN.")
            log_akses("🛡️ Security Mode", "Nonaktifkan")
with col2:
    if st.session_state.pintu_terbuka and st.button("🔒 Kunci Pintu Manual"):
        st.session_state.pintu_terbuka = False
        st.success("🔒 Pintu berhasil dikunci secara manual.")
        log_akses("🔒 Manual", "Kunci manual")

# ======================== FORM INPUT PIN ========================
with st.form("form_pin"):
    input_pin = st.text_input("Masukkan PIN Anda:", type="password")
    submitted = st.form_submit_button("🔓 Buka Pintu / Akses")

if submitted:
    st.session_state.last_activity = time.time()

    if st.session_state.terkunci:
        st.error("🚨 Sistem terkunci. Silakan reset aplikasi.")
        log_akses("🚨 Gagal Akses", "Sistem terkunci")

    elif st.session_state.security_mode:
        st.error("🛡️ Akses ditolak! Security Mode sedang AKTIF.")
        log_akses("🛡️ Gagal Akses", "Security Mode aktif")

    elif input_pin == st.session_state.pin_terdaftar:
        st.success("✅ Akses diterima. Pintu terbuka!")
        st.session_state.pintu_terbuka = True
        st.session_state.percobaan = 0
        log_akses("✅ Akses Berhasil", "PIN sesuai")

    elif input_pin == pin_master:
        st.info("🔐 Admin Mode aktif. Ganti PIN pengguna di bawah ini.")
        new_pin = st.text_input("Masukkan PIN baru (4 digit):", max_chars=4, key="ubah_pin")
        if new_pin:
            if len(new_pin) == 4 and new_pin.isdigit():
                st.session_state.pin_terdaftar = new_pin
                st.success("✅ PIN berhasil diubah.")
                st.session_state.percobaan = 0
                log_akses("🔐 Admin", "PIN berhasil diubah")
            else:
                st.error("❌ PIN harus 4 digit angka.")

    else:
        st.session_state.percobaan += 1
        sisa = max_attempt - st.session_state.percobaan
        st.warning(f"❌ PIN salah! Sisa percobaan: {sisa}")
        log_akses("❌ PIN Salah", f"Sisa percobaan: {sisa}")

        if st.session_state.percobaan >= max_attempt:
            st.session_state.terkunci = True
            st.error("🚨 Terlalu banyak percobaan! Sistem terkunci.")
            log_akses("🚨 Sistem Terkunci", "Terlalu banyak percobaan")
            kirim_email("🚨 Alarm! Sistem Terkunci",
                        "Terdeteksi percobaan akses 3x gagal. Sistem dikunci otomatis.")

# ======================== STATUS PINTU ========================
st.markdown("---")
if st.session_state.pintu_terbuka:
    st.success("🚪 Status Pintu: TERBUKA")
else:
    st.info("🚪 Status Pintu: TERKUNCI")

if st.session_state.security_mode:
    st.warning("🛡️ Security Mode AKTIF")

# ======================== RESET SISTEM ========================
if st.session_state.terkunci:
    if st.button("🔄 Reset Sistem"):
        st.session_state.percobaan = 0
        st.session_state.terkunci = False
        st.success("✅ Sistem berhasil direset.")
        log_akses("🔄 Reset", "Reset manual oleh user")

check_auto_lock()

# ======================== COUNTDOWN AUTO LOCK ========================
if st.session_state.pintu_terbuka:
    now = time.time()
    sisa_waktu = int(waktu_timeout - (now - st.session_state.last_activity))
    if sisa_waktu > 0:
        st.info(f"⏳ Pintu akan terkunci otomatis dalam {sisa_waktu} detik jika tidak ada aktivitas.")
    else:
        st.success("🔒 Pintu terkunci otomatis.")

# ======================== RIWAYAT AKSES ========================
st.markdown("---")
if st.checkbox("📜 Tampilkan Riwayat Akses"):
    conn = sqlite3.connect('log_akses.db')
    df = pd.read_sql_query("SELECT * FROM log_akses ORDER BY waktu DESC", conn)
    st.dataframe(df)
    conn.close()
