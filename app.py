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

# --- 1. AYARLAR ---
st.set_page_config(page_title="Yurt Takip Pro", page_icon="🏫", layout="wide")

# --- GÜVENLİK VE LINK ---

SHEET_LINKI = "https://docs.google.com/spreadsheets/d/14vue2y63WXYE6-uXqtiEUgGU-yVrBCJy6R6Nj_EdyMI/edit?gid=0#gid=0" # KENDİ LİNKİNİ UNUTMA!

# --- CSS TASARIM ---
st.markdown("""
<style>
    div[data-testid="stButton"] button {width: 100%; border-radius: 8px; border: 1px solid #ddd;}
    div[data-testid="stButton"] button:hover {border-color: #888;}
    .stSuccess, .stInfo, .stWarning {padding: 10px; border-radius: 5px; font-weight: bold;}
    div[data-testid="stCaptionContainer"] {
        text-align: center;
        font-weight: bold;
        color: #333;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

PASTEL_RENKLER = ["#FFEBEE", "#E3F2FD", "#E8F5E9", "#FFF3E0", "#F3E5F5", "#E0F7FA", "#FFFDE7", "#FBE9E7", "#ECEFF1", "#FCE4EC"]

# --- GİRİŞ KONTROLÜ ---
def giris_kontrol():
    if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False
    if not st.session_state.giris_yapildi:
        st.header("🔒 Yurt Yönetim Paneli")
        sifre = st.text_input("Giriş Şifresi:", type="password")
        if st.button("Giriş Yap"):
            if sifre == ADMIN_SIFRESI:
                st.session_state.giris_yapildi = True
                st.success("Giriş Başarılı!")
                time.sleep(0.5)
                st.rerun()
            else: st.error("Hatalı Şifre!")
        return False
    return True

if not giris_kontrol(): st.stop()

# --- 2. VERİTABANI BAĞLANTISI (AKILLI HİBRİT MOD) ---
def get_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # 1. ADIM: Bilgisayarındaki dosyayı kontrol et
    klasor = os.path.dirname(os.path.abspath(__file__))
    yerel_dosya = os.path.join(klasor, "anahtar.json")
    
    if os.path.exists(yerel_dosya):
        # Bilgisayardaysan bunu kullan
        creds = Credentials.from_service_account_file(yerel_dosya, scopes=scope)
    else:
        # 2. ADIM: İnternetteysen (Streamlit Cloud) gizli ayarlara bak
        try:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        except:
            st.error("🚨 KRİTİK HATA: Bağlantı anahtarı bulunamadı!")
            st.info("Bilgisayardaysan: 'anahtar.json' dosyası app.py yanında olmalı.")
            st.info("İnternetteysen: Streamlit Secrets ayarları yapılmalı.")
            st.stop()
            
    return gspread.authorize(creds)

def get_main_sheet():
    return get_client().open_by_url(SHEET_LINKI).sheet1

def get_log_sheet():
    client = get_client(); ss = client.open_by_url(SHEET_LINKI)
    try: return ss.worksheet("GECMIS")
    except:
        ws = ss.add_worksheet("GECMIS", 1000, 12)
        ws.append_row(["Tarih", "Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Veli", "Veli Tel"])
        return ws

# --- VERİ ÇEKME ---
if "df" not in st.session_state:
    try:
        data = get_main_sheet().get_all_records()
        if not data:
            st.session_state.df = pd.DataFrame(columns=["Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Veli", "Veli Tel"])
        else:
            st.session_state.df = pd.DataFrame(data)
        
        cols = ["Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Veli", "Veli Tel"]
        for c in cols:
            if c not in st.session_state.df.columns: st.session_state.df[c] = "-"
        st.session_state.df = st.session_state.df.fillna("-")
    except Exception as e: st.error(f"Veri Hatası: {e}"); st.stop()

# --- FONKSİYONLAR ---
def buluta_kaydet():
    try:
        sheet = get_main_sheet()
        veriler = [st.session_state.df.columns.tolist()] + st.session_state.df.astype(str).values.tolist()
        sheet.clear(); sheet.update(veriler)
        st.toast("✅ Veriler Buluta Kaydedildi!", icon="☁️")
    except Exception as e: st.error(f"Hata: {e}")

def gunu_bitir():
    try:
        bugun = datetime.now().strftime("%d.%m.%Y")
        df_log = st.session_state.df.copy()
        df_log.insert(0, "Tarih", bugun)
        get_log_sheet().append_rows(df_log.astype(str).values.tolist())
        st.success(f"✅ Arşivlendi: {bugun}"); st.balloons()
    except Exception as e: st.error(f"Hata: {e}")

def create_pdf(df, belletmen):
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=A4); width, height = A4
    try: pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf')); font = 'Arial'
    except: font = 'Helvetica'
    
    c.setFont(font, 16); c.drawString(40, height-50, "YURT YOKLAMA LİSTESİ")
    c.setFont(font, 10); c.drawString(40, height-75, f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    c.drawRightString(width-40, height-75, f"Belletmen: {belletmen}"); c.line(40, height-85, width-40, height-85)
    
    pdf_data = [["Ad Soyad", "No", "Oda", "Durum", "İzin", "Etüd", "Yat", "Mesaj"]]
    for _, r in df.sort_values("Oda No").iterrows():
        durum_txt = str(r['Durum'])
        izin_txt = "-" if durum_txt=="Yurtta" else str(r['İzin Durumu'])
        etud_txt = str(r['Etüd']).replace("✅ Var","VAR").replace("❌ Yok","YOK").replace("⚪","-")
        yat_txt = str(r['Yat']).replace("✅ Var","VAR").replace("❌ Yok","YOK").replace("⚪","-")
        mesaj_txt = str(r['Mesaj Durumu']).replace("✅ ","")
        pdf_data.append([str(r['Ad Soyad']), str(r['Numara']), str(r['Oda No']), durum_txt, izin_txt, etud_txt, yat_txt, mesaj_txt])
        
    t = Table(pdf_data, colWidths=[100,30,40,50,50,40,40,140])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.5,colors.black),('FONTNAME',(0,0),(-1,-1),font),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    t.wrapOn(c, width, height); t.drawOn(c, 40, height-(110+len(pdf_data)*20))
    c.save(); buffer.seek(0); return buffer

def get_renk(oda):
    try: return PASTEL_RENKLER[sum(ord(c) for c in str(oda)) % len(PASTEL_RENKLER)]
    except: return "#FFFFFF"

def wp_link(tel, msj):
    t = str(tel).replace(' ','').lstrip('0').replace('-','').replace('.','')
    return f"https://wa.me/90{t}?text={urllib.parse.quote(msj)}" if t else "#"

# Durum Değiştiriciler
def durum_deg(i): st.session_state.df.at[i,"Durum"]={"Yurtta":"İzinli","İzinli":"Evde","Evde":"Yurtta"}.get(st.session_state.df.at[i,"Durum"],"Yurtta"); st.session_state.df.at[i,"Mesaj Durumu"]="-"
def izin_deg(i): st.session_state.df.at[i,"İzin Durumu"]="İzin Yok" if st.session_state.df.at[i,"İzin Durumu"]=="İzin Var" else "İzin Var"
def ey_deg(i,tip): st.session_state.df.at[i,tip]={"⚪":"✅ Var","✅ Var":"❌ Yok","❌ Yok":"⚪"}.get(st.session_state.df.at[i,tip],"⚪")
def msj_at(i, m):
    mevcut = str(st.session_state.df.at[i,"Mesaj Durumu"])
    if mevcut in ["-", "nan"]: son = m
    elif "Genel" in m: son = m
    else:
        e = "Etüd" in mevcut or "Etüd" in m; y = "Yat" in mevcut or "Yat" in m
        son = "Etüd ve Yat Msj. Atıldı" if e and y else ("Etüd Msj. Atıldı" if e else ("Yat Msj. Atıldı" if y else m))
    st.session_state.df.at[i,"Mesaj Durumu"] = son

# --- ARAYÜZ ---
st.title("☁️ Yurt Takip - Online")

# Üst Bar
c_bel, c_save, c_arsiv = st.columns([2, 1, 1])
if "belletmen_adi" not in st.session_state: st.session_state.belletmen_adi = ""
with c_bel: st.session_state.belletmen_adi = st.text_input("👮 Belletmen", st.session_state.get("belletmen_adi",""))
with c_save: 
    st.write(""); st.write("")
    if st.button("☁️ KAYDET", type="primary"): buluta_kaydet()
with c_arsiv:
    st.write(""); st.write("")
    if st.button("🌙 GÜNÜ BİTİR"): gunu_bitir()

menu = st.sidebar.radio("Menü", ["📋 Yoklama Listesi", "🗄️ Geçmiş Kayıtlar", "➕ Öğrenci Ekle"])
st.sidebar.markdown("---")
if st.sidebar.button("🔒 Güvenli Çıkış"): st.session_state.giris_yapildi = False; st.rerun()
if st.sidebar.button("📄 PDF Olarak İndir"):
    pdf = create_pdf(st.session_state.df, st.session_state.belletmen_adi)
    st.sidebar.download_button("⬇️ İndir", pdf, "yurt_yoklama.pdf", "application/pdf")

if menu=="📋 Yoklama Listesi":
    ara = st.text_input("🔍 İsim veya Oda No Ara")
    f_df = st.session_state.df[st.session_state.df.astype(str).apply(lambda x: x.str.contains(ara, case=False)).any(axis=1)] if ara else st.session_state.df
    
    # --- BAŞLIKLAR (DÜZELTİLDİ) ---
    col_spec = [2.8, 1.2, 1.2, 1.2, 1.2, 1.2, 1.8, 0.5]
    h1, h2, h3, h4, h5, h6, h7, h8 = st.columns(col_spec)
    h1.caption("Öğrenci Bilgisi")
    h2.caption("Oda")
    h3.caption("Genel Durum")
    h4.caption("İzin")
    h5.caption("Etüd Yoklama") # Yazı Geri Geldi
    h6.caption("Yat Yoklama")  # Yazı Geri Geldi
    h7.caption("Mesaj")
    h8.caption("Sil")

    for i in f_df.sort_values("Oda No").index:
        r = f_df.loc[i]; c = st.columns(col_spec)
        
        # İsim
        c[0].markdown(f"<div style='background:{get_renk(r['Oda No'])};padding:5px;border-radius:5px;'><b>{r['Ad Soyad']}</b><br><small>{r['Numara']}</small></div>", unsafe_allow_html=True)
        # Oda
        c[1].markdown(f"<div style='background:{get_renk(r['Oda No'])};padding:5px;border-radius:5px;text-align:center;'><b>{r['Oda No']}</b></div>", unsafe_allow_html=True)
        
        # Durum
        durum_ikon = {"Yurtta": "🟢", "İzinli": "🟡", "Evde": "🔵"}.get(r['Durum'], "⚪")
        if c[2].button(f"{durum_ikon} {r['Durum']}", key=f"d{i}"): durum_deg(i); st.rerun()
        
        # İzin
        if r['Durum']!="Yurtta": 
            btn_s = "primary" if r['İzin Durumu']=="İzin Yok" else "secondary"
            btn_i = "✅" if r['İzin Durumu']=="İzin Var" else "⛔"
            if c[3].button(btn_i, key=f"i{i}", type=btn_s): izin_deg(i); st.rerun()
        else: c[3].markdown("<center style='color:#ccc;padding-top:10px;'>-</center>", unsafe_allow_html=True)
        
        # Yasal İzin Kontrolü
        yasal = r['Durum']!="Yurtta" and (r['Durum']=="İzinli" or r['İzin Durumu']=="İzin Var")
        
        if not yasal:
            # Etüd
            es = "primary" if "Yok" in str(r['Etüd']) else "secondary"
            if c[4].button(str(r['Etüd']), key=f"e{i}", type=es): ey_deg(i,"Etüd"); st.rerun()
            # Yat
            ys = "primary" if "Yok" in str(r['Yat']) else "secondary"
            if c[5].button(str(r['Yat']), key=f"y{i}", type=ys): ey_deg(i,"Yat"); st.rerun()
            
            # Mesaj
            ek = "Yok" in str(r['Etüd']); yk = "Yok" in str(r['Yat']); evk = (r['Durum']=="Evde" and r['İzin Durumu']=="İzin Yok")
            if evk or ek or yk:
                lbl = f"✅ {r['Mesaj Durumu']}" if r['Mesaj Durumu']!="-" else "💬 Mesaj"
                with c[6].popover(lbl, use_container_width=True):
                    if ek:
                        st.link_button("📤 WP (Etüd)", wp_link(r['Veli Tel'], f"Etüd yoklamasında {r['Ad Soyad']} yoktur."))
                        if st.button("✅ İşaretle", key=f"me{i}"): msj_at(i, "Etüd Msj. Atıldı"); st.rerun()
                    if yk:
                        st.link_button("📤 WP (Yat)", wp_link(r['Veli Tel'], f"Yat yoklamasında {r['Ad Soyad']} yoktur."))
                        if st.button("✅ İşaretle", key=f"my{i}"): msj_at(i, "Yat Msj. Atıldı"); st.rerun()
                    if evk:
                        st.link_button("📤 WP (Kaçak)", wp_link(r['Veli Tel'], f"{r['Ad Soyad']} izinsiz yurtta yoktur."))
                        if st.button("✅ İşaretle", key=f"mk{i}"): msj_at(i, "Genel Uyarı Atıldı"); st.rerun()
            else: c[6].markdown("<center style='color:#ccc;padding-top:10px;'>-</center>", unsafe_allow_html=True)
        else:
            c[4].markdown("<center style='color:#ccc;padding-top:10px;'>-</center>", unsafe_allow_html=True)
            c[5].markdown("<center style='color:#ccc;padding-top:10px;'>-</center>", unsafe_allow_html=True)
            c[6].markdown("<center style='color:#ccc;padding-top:10px;'>-</center>", unsafe_allow_html=True)
            
        # Sil Butonu
        if c[7].button("🗑️", key=f"del{i}"):
            st.session_state.df = st.session_state.df.drop(i).reset_index(drop=True)
            buluta_kaydet()
            st.rerun()
            
        st.divider()

elif menu=="🗄️ Geçmiş Kayıtlar":
    st.header("🗄️ Geçmiş Kayıtlar")
    try:
        d = pd.DataFrame(get_log_sheet().get_all_records())
        if not d.empty:
            sel = st.selectbox("Tarih Seçin", d["Tarih"].unique())
            goster = d[d["Tarih"]==sel]
            st.dataframe(goster, use_container_width=True)
            st.info(f"{sel} tarihinde {len(goster[goster['Durum']=='Yurtta'])} öğrenci yurttaymış.")
        else: st.warning("Henüz arşivlenmiş kayıt yok.")
    except Exception as e: st.error(f"Hata: {e}")

elif menu=="➕ Öğrenci Ekle":
    st.subheader("Yeni Öğrenci Ekle")
    with st.form("a"):
        c1, c2 = st.columns(2); nm=c1.text_input("Ad Soyad"); no=c2.text_input("Numara")
        od=c1.text_input("Oda No"); vl=c2.text_input("Veli Adı"); tl=c1.text_input("Veli Tel")
        if st.form_submit_button("Kaydet"):
             yeni = pd.DataFrame([{"Ad Soyad":nm,"Numara":no,"Oda No":od,"Durum":"Yurtta","İzin Durumu":"İzin Var","Etüd":"⚪","Yat":"⚪","Mesaj Durumu":"-","Veli":vl,"Veli Tel":tl}])
             st.session_state.df = pd.concat([st.session_state.df, yeni], ignore_index=True)
             buluta_kaydet(); st.success("Öğrenci eklendi!")

