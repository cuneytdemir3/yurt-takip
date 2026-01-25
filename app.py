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
st.set_page_config(page_title="Yurt Takip Mobil", page_icon="📱", layout="centered") 
# Not: Layout 'centered' yaptık ki mobilde daha derli toplu dursun.

# --- GÜVENLİK VE LINK ---
SHEET_LINKI = "https://docs.google.com/spreadsheets/d/BURAYA_LINKINI_YAPISTIR/edit" 

# --- CSS TASARIM (MOBİL İÇİN ÖZEL) ---
st.markdown("""
<style>
    /* Butonları mobilde parmakla basılacak kadar büyük yap */
    div[data-testid="stButton"] button {
        width: 100%;
        border-radius: 12px;
        border: 1px solid #ddd;
        padding: 15px 5px; 
        font-size: 16px;
        font-weight: bold;
    }
    div[data-testid="stButton"] button:hover {
        border-color: #888;
        background-color: #f0f2f6;
    }
    /* Expander (Açılır Kutu) başlıklarını güzelleştir */
    .streamlit-expanderHeader {
        font-size: 18px !important;
        font-weight: bold !important;
        background-color: #f8f9fa;
        border-radius: 10px;
    }
    /* Başarı/Hata kutularını mobilde düzelt */
    .stSuccess, .stInfo, .stWarning {
        padding: 10px; 
        border-radius: 8px; 
    }
</style>
""", unsafe_allow_html=True)

PASTEL_RENKLER = ["#FFEBEE", "#E3F2FD", "#E8F5E9", "#FFF3E0", "#F3E5F5", "#E0F7FA", "#FFFDE7", "#FBE9E7", "#ECEFF1", "#FCE4EC"]

# --- GİRİŞ KONTROLÜ ---
def giris_kontrol():
    try: GERCEK_SIFRE = st.secrets["genel"]["admin_sifresi"]
    except: GERCEK_SIFRE = "1234"

    if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False
    
    if not st.session_state.giris_yapildi:
        st.markdown("<h2 style='text-align: center;'>🔒 Mobil Giriş</h2>", unsafe_allow_html=True)
        sifre = st.text_input("Şifre", type="password", label_visibility="collapsed", placeholder="Şifrenizi Girin")
        if st.button("Giriş Yap", type="primary"):
            if sifre == GERCEK_SIFRE:
                st.session_state.giris_yapildi = True
                st.success("Giriş Başarılı!")
                time.sleep(0.5)
                st.rerun()
            else: st.error("Hatalı Şifre!")
        return False
    return True

if not giris_kontrol(): st.stop()

# --- 2. VERİTABANI BAĞLANTISI ---
def get_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    klasor = os.path.dirname(os.path.abspath(__file__))
    yerel_dosya = os.path.join(klasor, "anahtar.json")
    
    if os.path.exists(yerel_dosya):
        return gspread.authorize(Credentials.from_service_account_file(yerel_dosya, scopes=scope))
    else:
        try:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            return gspread.authorize(creds)
        except Exception as e:
            st.error("🚨 Bağlantı Hatası: Secrets ayarlarını kontrol et.")
            st.stop()

def get_main_sheet(): return get_client().open_by_url(SHEET_LINKI).sheet1

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
        if not data: st.session_state.df = pd.DataFrame(columns=["Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Veli", "Veli Tel"])
        else: st.session_state.df = pd.DataFrame(data)
        for c in ["Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Veli", "Veli Tel"]:
            if c not in st.session_state.df.columns: st.session_state.df[c] = "-"
        st.session_state.df = st.session_state.df.fillna("-")
    except Exception as e: st.error(f"Veri Hatası: {e}"); st.stop()

# --- FONKSİYONLAR ---
def buluta_kaydet():
    try:
        get_main_sheet().update([st.session_state.df.columns.tolist()] + st.session_state.df.astype(str).values.tolist())
        st.toast("✅ Kaydedildi!", icon="☁️")
    except Exception as e: st.error(f"Hata: {e}")

def gunu_bitir():
    try:
        bugun = datetime.now().strftime("%d.%m.%Y"); df_log = st.session_state.df.copy(); df_log.insert(0, "Tarih", bugun)
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
        durum_txt = str(r['Durum']); izin_txt = "-" if durum_txt=="Yurtta" else str(r['İzin Durumu'])
        etud_txt = str(r['Etüd']).replace("✅ Var","VAR").replace("❌ Yok","YOK").replace("⚪","-")
        yat_txt = str(r['Yat']).replace("✅ Var","VAR").replace("❌ Yok","YOK").replace("⚪","-")
        mesaj_txt = str(r['Mesaj Durumu']).replace("✅ ","")
        pdf_data.append([str(r['Ad Soyad']), str(r['Numara']), str(r['Oda No']), durum_txt, izin_txt, etud_txt, yat_txt, mesaj_txt])
    t = Table(pdf_data, colWidths=[100,30,40,50,50,40,40,140])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.5,colors.black),('FONTNAME',(0,0),(-1,-1),font),('FONTSIZE',(0,0),(-1,-1),8)]))
    t.wrapOn(c, width, height); t.drawOn(c, 40, height-(110+len(pdf_data)*20)); c.save(); buffer.seek(0); return buffer

def wp_link(tel, msj):
    t = str(tel).replace(' ','').lstrip('0').replace('-','').replace('.','')
    return f"https://wa.me/90{t}?text={urllib.parse.quote(msj)}" if t else "#"

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

# --- ARAYÜZ (MOBİL TASARIM) ---
st.title("📱 Yurt Takip")

# Üst Butonlar (Yan Yana)
col1, col2 = st.columns(2)
with col1:
    if st.button("☁️ KAYDET", type="primary"): buluta_kaydet()
with col2:
    if st.button("🌙 ARŞİVLE"): gunu_bitir()

# Menü (Mobilde Radio Button çok yer kaplar, Selectbox daha iyi)
menu = st.selectbox("Menü Seçiniz", ["📋 Yoklama Listesi", "🗄️ Geçmiş Kayıtlar", "➕ Öğrenci Ekle", "📄 PDF İndir"])

if menu == "📄 PDF İndir":
    belletmen = st.text_input("Belletmen Adı")
    if belletmen:
        pdf = create_pdf(st.session_state.df, belletmen)
        st.download_button("⬇️ PDF İndir", pdf, "yoklama.pdf", "application/pdf", type="primary")

if menu == "📋 Yoklama Listesi":
    ara = st.text_input("🔍 Öğrenci Ara", placeholder="İsim veya Oda No...")
    
    f_df = st.session_state.df
    if ara:
        f_df = f_df[f_df.astype(str).apply(lambda x: x.str.contains(ara, case=False)).any(axis=1)]
    
    st.write(f"**Toplam:** {len(f_df)} Öğrenci")
    st.divider()

    # --- KART GÖRÜNÜMÜ (MOBİL DOSTU) ---
    for i in f_df.sort_values("Oda No").index:
        r = f_df.loc[i]
        
        # Başlık için İkon Belirle
        durum_ikon = {"Yurtta": "🟢", "İzinli": "🟡", "Evde": "🔵"}.get(r['Durum'], "⚪")
        
        # KART BAŞLIĞI: [Renk] [Oda] - [İsim]
        baslik = f"{durum_ikon} {r['Oda No']} - {r['Ad Soyad']}"
        
        with st.expander(baslik):
            # 1. SATIR: DURUM VE İZİN
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Genel Durum")
                if st.button(f"{r['Durum']}", key=f"d{i}", use_container_width=True): durum_deg(i); st.rerun()
            with c2:
                st.caption("İzin")
                if r['Durum'] != "Yurtta":
                    btn_stil = "primary" if r['İzin Durumu']=="İzin Yok" else "secondary"
                    ikon = "✅ İzinli" if r['İzin Durumu']=="İzin Var" else "⛔ İzinsiz"
                    if st.button(ikon, key=f"i{i}", type=btn_stil, use_container_width=True): izin_deg(i); st.rerun()
                else:
                    st.info("-")

            # Yasal Kontrol
            yasal = r['Durum']!="Yurtta" and (r['Durum']=="İzinli" or r['İzin Durumu']=="İzin Var")
            
            if not yasal:
                st.markdown("---")
                # 2. SATIR: ETÜD VE YAT
                c3, c4 = st.columns(2)
                with c3:
                    st.caption("📖 Etüd")
                    stil = "primary" if "Yok" in str(r['Etüd']) else "secondary"
                    if st.button(str(r['Etüd']), key=f"e{i}", type=stil, use_container_width=True): ey_deg(i,"Etüd"); st.rerun()
                with c4:
                    st.caption("🛏️ Yat")
                    stil = "primary" if "Yok" in str(r['Yat']) else "secondary"
                    if st.button(str(r['Yat']), key=f"y{i}", type=stil, use_container_width=True): ey_deg(i,"Yat"); st.rerun()

                # 3. SATIR: MESAJ VE WHATSAPP
                ek = "Yok" in str(r['Etüd']); yk = "Yok" in str(r['Yat']); evk = (r['Durum']=="Evde" and r['İzin Durumu']=="İzin Yok")
                if evk or ek or yk:
                    st.markdown("---")
                    st.warning(f"Durum: {r['Mesaj Durumu']}")
                    c5, c6 = st.columns(2)
                    with c5:
                        if ek: st.link_button("💬 WP (Etüd)", wp_link(r['Veli Tel'], f"Etüd yoklamasında {r['Ad Soyad']} yoktur."), use_container_width=True)
                        elif yk: st.link_button("💬 WP (Yat)", wp_link(r['Veli Tel'], f"Yat yoklamasında {r['Ad Soyad']} yoktur."), use_container_width=True)
                        elif evk: st.link_button("💬 WP (Kaçak)", wp_link(r['Veli Tel'], f"{r['Ad Soyad']} izinsiz yurtta yoktur."), use_container_width=True)
                    with c6:
                        if st.button("✅ Mesaj Atıldı", key=f"m{i}", use_container_width=True): msj_at(i, "Msj Atıldı"); st.rerun()

            # 4. SATIR: SİL
            st.markdown("---")
            if st.button("🗑️ Öğrenciyi Sil", key=f"del{i}", type="secondary", use_container_width=True):
                st.session_state.df = st.session_state.df.drop(i).reset_index(drop=True)
                buluta_kaydet()
                st.rerun()

elif menu == "🗄️ Geçmiş Kayıtlar":
    st.subheader("Arşiv")
    try:
        d = pd.DataFrame(get_log_sheet().get_all_records())
        if not d.empty:
            sel = st.selectbox("Tarih Seçin", d["Tarih"].unique())
            st.dataframe(d[d["Tarih"]==sel], use_container_width=True)
        else: st.info("Kayıt yok.")
    except Exception as e: st.error(f"Hata: {e}")

elif menu == "➕ Öğrenci Ekle":
    st.subheader("Yeni Kayıt")
    with st.form("ekle"):
        nm=st.text_input("Ad Soyad"); no=st.text_input("Numara"); od=st.text_input("Oda No")
        vl=st.text_input("Veli Adı"); tl=st.text_input("Veli Tel (Başında 0 olmadan)")
        if st.form_submit_button("Öğrenciyi Kaydet", type="primary"):
             yeni = pd.DataFrame([{"Ad Soyad":nm,"Numara":no,"Oda No":od,"Durum":"Yurtta","İzin Durumu":"İzin Var","Etüd":"⚪","Yat":"⚪","Mesaj Durumu":"-","Veli":vl,"Veli Tel":tl}])
             st.session_state.df = pd.concat([st.session_state.df, yeni], ignore_index=True)
             buluta_kaydet(); st.success("Eklendi!")

