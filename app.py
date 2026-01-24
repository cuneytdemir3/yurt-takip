import streamlit as st
import pandas as pd
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import os
from datetime import datetime
import time
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="Yurt Takip Pro", page_icon="🏫", layout="wide")

# --- GÜVENLİK VE LINK ---
ADMIN_SIFRESI = "2008" # Şifreni buraya yaz
SHEET_LINKI = "https://docs.google.com/spreadsheets/d/14vue2y63WXYE6-uXqtiEUgGU-yVrBCJy6R6Nj_EdyMI/edit?gid=0#gid=0" # Linkini buraya yaz

# --- CSS ---
st.markdown("""
<style>
    div[data-testid="stButton"] button {width: 100%; border-radius: 8px; border: 1px solid #ddd;}
    div[data-testid="stButton"] button:hover {border-color: #888;}
    .stSuccess, .stInfo, .stWarning {padding: 10px; border-radius: 5px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)
PASTEL_RENKLER = ["#FFEBEE", "#E3F2FD", "#E8F5E9", "#FFF3E0", "#F3E5F5", "#E0F7FA", "#FFFDE7", "#FBE9E7", "#ECEFF1", "#FCE4EC"]

# --- GİRİŞ KONTROLÜ ---
def giris_kontrol():
    if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False
    if not st.session_state.giris_yapildi:
        st.header("🔒 Yurt Yönetim Paneli"); sifre = st.text_input("Şifre:", type="password")
        if st.button("Giriş Yap"):
            if sifre == ADMIN_SIFRESI: st.session_state.giris_yapildi = True; st.success("Giriş Başarılı!"); time.sleep(0.5); st.rerun()
            else: st.error("Hatalı Şifre!")
        return False
    return True

if not giris_kontrol(): st.stop()

# --- 2. VERİTABANI BAĞLANTISI (AKILLI MOD) ---
def get_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # 1. YÖNTEM: İNTERNETTEYSE (Streamlit Cloud Secrets)
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        
    # 2. YÖNTEM: BİLGİSAYARDAYSA (Yerel Dosya)
    else:
        klasor = os.path.dirname(os.path.abspath(__file__))
        dosya = os.path.join(klasor, "anahtar.json")
        if not os.path.exists(dosya): st.error("🚨 Anahtar dosyası bulunamadı!"); st.stop()
        creds = Credentials.from_service_account_file(dosya, scopes=scope)
        
    return gspread.authorize(creds)

def get_main_sheet():
    return get_client().open_by_url(SHEET_LINKI).sheet1

def get_log_sheet():
    client = get_client(); ss = client.open_by_url(SHEET_LINKI)
    try: return ss.worksheet("GECMIS")
    except: ws = ss.add_worksheet("GECMIS", 1000, 12); ws.append_row(["Tarih", "Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Veli", "Veli Tel"]); return ws

# --- VERİ ÇEKME ---
if "df" not in st.session_state:
    try:
        data = get_main_sheet().get_all_records()
        st.session_state.df = pd.DataFrame(data) if data else pd.DataFrame(columns=["Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Veli", "Veli Tel"])
        for c in ["Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Veli", "Veli Tel"]:
            if c not in st.session_state.df.columns: st.session_state.df[c] = "-"
        st.session_state.df = st.session_state.df.fillna("-")
    except Exception as e: st.error(f"Veri Hatası: {e}"); st.stop()

# --- FONKSİYONLAR ---
def buluta_kaydet():
    try: get_main_sheet().update([st.session_state.df.columns.tolist()] + st.session_state.df.astype(str).values.tolist()); st.toast("✅ Kaydedildi!", icon="☁️")
    except Exception as e: st.error(f"Hata: {e}")

def gunu_bitir():
    try:
        bugun = datetime.now().strftime("%d.%m.%Y"); df_log = st.session_state.df.copy(); df_log.insert(0, "Tarih", bugun)
        get_log_sheet().append_rows(df_log.astype(str).values.tolist()); st.success(f"✅ Arşivlendi: {bugun}"); st.balloons()
    except Exception as e: st.error(f"Hata: {e}")

def create_pdf(df, belletmen):
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=A4); width, height = A4
    try: pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf')); font = 'Arial'
    except: font = 'Helvetica'
    c.setFont(font, 16); c.drawString(40, height-50, "YURT YOKLAMA LİSTESİ")
    c.setFont(font, 10); c.drawString(40, height-75, f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}"); c.drawRightString(width-40, height-75, f"Belletmen: {belletmen}"); c.line(40, height-85, width-40, height-85)
    pdf_data = [["Ad Soyad", "No", "Oda", "Durum", "İzin", "Etüd", "Yat", "Mesaj"]]
    for _, r in df.sort_values("Oda No").iterrows():
        pdf_data.append([str(r['Ad Soyad']), str(r['Numara']), str(r['Oda No']), str(r['Durum']), "-" if r['Durum']=="Yurtta" else str(r['İzin Durumu']), str(r['Etüd']).replace("✅ Var","VAR").replace("❌ Yok","YOK").replace("⚪","-"), str(r['Yat']).replace("✅ Var","VAR").replace("❌ Yok","YOK").replace("⚪","-"), str(r['Mesaj Durumu']).replace("✅ ","")])
    t = Table(pdf_data, colWidths=[100,30,40,50,50,40,40,140]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.5,colors.black),('FONTNAME',(0,0),(-1,-1),font),('FONTSIZE',(0,0),(-1,-1),8)])); t.wrapOn(c, width, height); t.drawOn(c, 40, height-(110+len(pdf_data)*20)); c.save(); buffer.seek(0); return buffer

def get_renk(oda): return PASTEL_RENKLER[sum(ord(c) for c in str(oda)) % len(PASTEL_RENKLER)]
def wp_link(tel, msj): return f"https://wa.me/{str(tel).replace(' ','').lstrip('0').replace('-','')}?text={urllib.parse.quote(msj)}" if str(tel).strip() else "#"

def durum_deg(i): st.session_state.df.at[i,"Durum"]={"Yurtta":"İzinli","İzinli":"Evde","Evde":"Yurtta"}.get(st.session_state.df.at[i,"Durum"],"Yurtta"); st.session_state.df.at[i,"Mesaj Durumu"]="-"
def izin_deg(i): st.session_state.df.at[i,"İzin Durumu"]="İzin Yok" if st.session_state.df.at[i,"İzin Durumu"]=="İzin Var" else "İzin Var"
def ey_deg(i,tip): st.session_state.df.at[i,tip]={"⚪":"✅ Var","✅ Var":"❌ Yok","❌ Yok":"⚪"}.get(st.session_state.df.at[i,tip],"⚪")
def msj_at(i, m): st.session_state.df.at[i,"Mesaj Durumu"]=m

# --- ARAYÜZ ---
st.title("☁️ Yurt Takip - Online"); c1, c2 = st.columns([2,1])
with c1: st.session_state.belletmen_adi = st.text_input("👮 Belletmen", st.session_state.get("belletmen_adi",""))
with c2: 
    if st.button("☁️ KAYDET", type="primary"): buluta_kaydet()
    if st.button("🌙 GÜNÜ BİTİR"): gunu_bitir()

menu = st.sidebar.radio("Menü", ["📋 Yoklama", "🗄️ Geçmiş", "➕ Ekle"])
if st.sidebar.button("🔒 Çıkış"): st.session_state.giris_yapildi = False; st.rerun()
if st.sidebar.button("📄 PDF"): st.sidebar.download_button("İndir", create_pdf(st.session_state.df, st.session_state.belletmen_adi), "yoklama.pdf")

if menu=="📋 Yoklama":
    ara = st.text_input("🔍 Ara"); f_df = st.session_state.df[st.session_state.df.astype(str).apply(lambda x: x.str.contains(ara, case=False)).any(axis=1)] if ara else st.session_state.df
    for i in f_df.sort_values("Oda No").index:
        r = f_df.loc[i]; c = st.columns([2.5,1,1.2,1.2,1.2,1.2,1.8,0.5])
        c[0].markdown(f"<div style='background:{get_renk(r['Oda No'])};padding:5px;border-radius:5px;'><b>{r['Ad Soyad']}</b><br><small>{r['Numara']}</small></div>", unsafe_allow_html=True)
        c[1].info(f"{r['Oda No']}")
        if c[2].button(f"{r['Durum']}", key=f"d{i}"): durum_deg(i); st.rerun()
        if r['Durum']!="Yurtta": 
            if c[3].button("✅" if r['İzin Durumu']=="İzin Var" else "⛔", key=f"i{i}"): izin_deg(i); st.rerun()
        else: c[3].write("-")
        
        yasal = r['Durum']!="Yurtta" and (r['Durum']=="İzinli" or r['İzin Durumu']=="İzin Var")
        if not yasal:
            if c[4].button(r['Etüd'], key=f"e{i}"): ey_deg(i,"Etüd"); st.rerun()
            if c[5].button(r['Yat'], key=f"y{i}"): ey_deg(i,"Yat"); st.rerun()
            if "Yok" in str(r['Etüd']) or "Yok" in str(r['Yat']) or (r['Durum']=="Evde" and r['İzin Durumu']=="İzin Yok"):
                with c[6].popover(f"✅ {r['Mesaj Durumu']}" if r['Mesaj Durumu']!="-" else "💬 Mesaj"):
                    st.link_button("Whatsapp", wp_link(r['Veli Tel'], f"Sayın Veli, {r['Ad Soyad']} yoklamada yoktur."))
                    if st.button("İşaretle", key=f"m{i}"): msj_at(i, "Msj Atıldı"); st.rerun()
        else: c[4].write("-"); c[5].write("-"); c[6].write("-")
        c[7].write("")
elif menu=="🗄️ Geçmiş":
    d = pd.DataFrame(get_log_sheet().get_all_records()); 
    if not d.empty: sel = st.selectbox("Tarih", d["Tarih"].unique()); st.dataframe(d[d["Tarih"]==sel])
elif menu=="➕ Ekle":
    with st.form("a"):
        nm=st.text_input("Ad"); no=st.text_input("No"); od=st.text_input("Oda"); vl=st.text_input("Veli"); tl=st.text_input("Tel")
        if st.form_submit_button("Ekle"):
             st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([{"Ad Soyad":nm,"Numara":no,"Oda No":od,"Durum":"Yurtta","İzin Durumu":"İzin Var","Etüd":"⚪","Yat":"⚪","Mesaj Durumu":"-","Veli":vl,"Veli Tel":tl}])], ignore_index=True); buluta_kaydet(); st.success("Tamam")