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
from reportlab.lib.utils import simpleSplit
import os
import requests
from datetime import datetime
import time
import warnings

# SSL uyarılarını gizle
warnings.filterwarnings("ignore")

# --- MOBİL AYARLAR ---
st.set_page_config(page_title="Yurt Mobil", page_icon="📱", layout="centered")

# --- LİNK AYARI ---
SHEET_LINKI = "https://docs.google.com/spreadsheets/d/14vue2y63WXYE6-uXqtiEUgGU-yVrBCJy6R6Nj_EdyMI/edit?gid=0#gid=0"

# --- KAT RENKLERİ ---
KAT_RENKLERI = {
    "1. KAT": "#E3F2FD",
    "2. KAT": "#E8F5E9",
    "3. KAT": "#FFF3E0",
    "DİĞER": "#F3E5F5"
}

# --- MOBİL CSS ---
st.markdown("""
<style>
    div[data-testid="stButton"] button {
        width: 100%;
        border-radius: 12px;
        border: 1px solid #ddd;
        padding: 15px 5px; 
        font-size: 16px;
        font-weight: bold;
        min-height: 50px;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #f0f2f6;
        border-color: #333;
    }
    a[kind="primary"] {
        width: 100%;
        border-radius: 12px;
        text-align: center;
        padding: 15px 5px;
        font-weight: bold;
        text-decoration: none;
        display: inline-block;
        background-color: #25D366 !important;
        color: white !important;
        border: none;
        margin-bottom: 5px;
    }
    .streamlit-expanderHeader {
        font-size: 16px !important;
        font-weight: 700 !important;
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 10px;
        margin-bottom: 5px;
        color: #333 !important;
    }
    div[role="radiogroup"] {
        background-color: #f9f9f9;
        padding: 10px;
        border-radius: 10px;
        justify-content: center;
    }
    .stTextArea textarea {
        font-size: 16px;
        border-radius: 10px;
    }
    .kat-baslik {
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 15px;
        border-left: 5px solid #666;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- GİRİŞ SİSTEMİ ---
def giris_kontrol():
    try: GERCEK_SIFRE = st.secrets["genel"]["admin_sifresi"]
    except: GERCEK_SIFRE = "1234"

    if "mobil_giris" not in st.session_state: st.session_state.mobil_giris = False
    
    if not st.session_state.mobil_giris:
        st.markdown("<br><h1 style='text-align: center;'>📱 Mobil Giriş</h1>", unsafe_allow_html=True)
        sifre = st.text_input("Şifre", type="password", label_visibility="collapsed", placeholder="Şifreyi Girin")
        if st.button("Giriş Yap", type="primary"):
            if sifre == GERCEK_SIFRE:
                st.session_state.mobil_giris = True
                st.rerun()
            else: st.error("Hatalı Şifre!")
        return False
    return True

if not giris_kontrol(): st.stop()

# --- BAĞLANTI ---
def get_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error("🚨 Bağlantı Hatası! Secrets ayarlarını yaptın mı?")
        st.stop()

def get_sheet(): return get_client().open_by_url(SHEET_LINKI).sheet1
def get_log():
    c = get_client(); s = c.open_by_url(SHEET_LINKI)
    try: return s.worksheet("GECMIS")
    except: 
        ws = s.add_worksheet("GECMIS", 1000, 12)
        ws.append_row(["Tarih", "Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Baba Adı", "Anne Adı", "Baba Tel", "Anne Tel"])
        return ws

# --- VERİ YÖNETİMİ ---
SUTUNLAR = ["Ad Soyad", "Numara", "Oda No", "Durum", "İzin Durumu", "Etüd", "Yat", "Mesaj Durumu", "Baba Adı", "Anne Adı", "Baba Tel", "Anne Tel"]

if "tutanak_1" not in st.session_state: st.session_state.tutanak_1 = "Olumsuz bir durum yoktur."
if "tutanak_2" not in st.session_state: st.session_state.tutanak_2 = "Olumsuz bir durum yoktur."
if "tutanak_3" not in st.session_state: st.session_state.tutanak_3 = "Olumsuz bir durum yoktur."

if "df" not in st.session_state:
    try:
        d = get_sheet().get_all_records()
        st.session_state.df = pd.DataFrame(d) if d else pd.DataFrame(columns=SUTUNLAR)
        for c in SUTUNLAR:
            if c not in st.session_state.df.columns: st.session_state.df[c] = "-"
        st.session_state.df = st.session_state.df.fillna("-").astype(str)
    except Exception as e: st.error(f"Veri Hatası: {e}"); st.stop()

def kaydet():
    try: 
        get_sheet().update([st.session_state.df.columns.tolist()] + st.session_state.df.astype(str).values.tolist())
    except: st.error("Bağlantı Hatası! Kaydedilemedi.")

def arsivle():
    try:
        t = datetime.now().strftime("%d.%m.%Y"); d = st.session_state.df.copy(); d.insert(0, "Tarih", t)
        get_log().append_rows(d.astype(str).values.tolist()); st.success(f"✅ {t} Arşivlendi!"); st.balloons()
    except: st.error("Arşiv Hatası")

def sifirla_yeni_yoklama():
    st.session_state.df["Durum"] = "Belirsiz"; st.session_state.df["Etüd"] = "⚪"; st.session_state.df["Yat"] = "⚪"; st.session_state.df["Mesaj Durumu"] = "-"
    kaydet(); st.success("Sıfırlandı!"); time.sleep(1); st.rerun()

def kat_bul(oda_no):
    try:
        no = int(str(oda_no).strip())
        if 101 <= no <= 115: return "1. KAT"
        elif 201 <= no <= 215: return "2. KAT"
        elif 301 <= no <= 315: return "3. KAT"
        else: return "DİĞER"
    except: return "DİĞER"

# --- FONT YÖNETİCİSİ ---
def tr_font_getir():
    font_adi = "Roboto"
    font_yolu = "Roboto-Regular.ttf"
    if font_adi in pdfmetrics.getRegisteredFontNames(): return font_adi
    if not os.path.exists(font_yolu) or os.path.getsize(font_yolu) < 10000:
        try:
            url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
            r = requests.get(url, timeout=10, verify=False)
            if r.status_code == 200: 
                with open(font_yolu, 'wb') as f: f.write(r.content)
            else: return "Helvetica"
        except: return "Helvetica"
    try: pdfmetrics.registerFont(TTFont(font_adi, font_yolu)); return font_adi
    except: 
        try: os.remove(font_yolu)
        except: pass
        return "Helvetica"

def tr_upper(text):
    if not text: return ""
    return text.replace("i", "İ").replace("ı", "I").upper()

# --- PDF ---
def pdf_yap(df, b1, b2, b3, t1, t2, t3):
    b = BytesIO(); c = canvas.Canvas(b, pagesize=A4); w, h = A4
    font = tr_font_getir()
    secili_katlar = []
    if b1: secili_katlar.append("1. KAT")
    if b2: secili_katlar.append("2. KAT")
    if b3: secili_katlar.append("3. KAT")
    if not secili_katlar: secili_katlar = ["1. KAT", "2. KAT", "3. KAT", "DİĞER"]

    df_pdf = df.copy()
    df_pdf["Oda No"] = df_pdf["Oda No"].astype(str)
    df_pdf["_KAT"] = df_pdf["Oda No"].apply(kat_bul)
    df_pdf = df_pdf[df_pdf["_KAT"].isin(secili_katlar)]

    c.setFont(font, 16); c.drawString(40, h-50, "YURT YOKLAMA LİSTESİ")
    c.setFont(font, 10); c.drawString(40, h-75, f"Tarih: {datetime.now().strftime('%d.%m.%Y')}")
    c.setFont(font, 9)
    y_h = 50
    if b1: c.drawRightString(w-40, h-y_h, f"1. Kat: {tr_upper(b1)}"); y_h+=12
    if b2: c.drawRightString(w-40, h-y_h, f"2. Kat: {tr_upper(b2)}"); y_h+=12
    if b3: c.drawRightString(w-40, h-y_h, f"3. Kat: {tr_upper(b3)}")
    c.line(40, h-90, w-40, h-90)
    
    data = [["Ad Soyad", "Oda", "Drm", "İzin", "Etüd", "Yat", "Msj"]]
    for _, r in df_pdf.sort_values("Oda No").iterrows():
        drm_str = str(r['Durum']); d_kisa = "?" if (drm_str=="Belirsiz" or not drm_str) else drm_str[0]
        izn_str = str(r['İzin Durumu']); i_kisa="-" if (r['Durum']=="Yurtta" or not izn_str) else izn_str[0]
        data.append([str(r['Ad Soyad'])[:22], str(r['Oda No']), d_kisa, i_kisa, str(r['Etüd']).replace("✅ Var","+").replace("❌ Yok","-").replace("⚪",""), str(r['Yat']).replace("✅ Var","+").replace("❌ Yok","-").replace("⚪",""), "OK" if "Atıldı" in str(r['Mesaj Durumu']) else ""])
    
    t = Table(data, colWidths=[120, 30, 30, 30, 30, 30, 40]); 
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.black),('FONTNAME',(0,0),(-1,-1),font),('FONTSIZE',(0,0),(-1,-1),8)]))
    t.wrapOn(c, w, h); t.drawOn(c, 40, h-(110+len(data)*20))
    
    c.showPage(); c.setFont(font, 16); c.drawString(40, h-50, tr_upper("GÜNLÜK KAT TUTANAKLARI")); c.line(40, h-60, w-40, h-60); y_pos = h-100
    def yazdir_tutanak(baslik, metin, y):
        c.setFont(font, 12); c.setFillColor(colors.darkblue); c.drawString(40, y, baslik); y-=20
        c.setFont(font, 10); c.setFillColor(colors.black)
        for line in simpleSplit(metin, font, 10, w-80): c.drawString(40, y, line); y -= 15
        return y-30
    if b1: y_pos = yazdir_tutanak(f"1. KAT TUTANAĞI ({tr_upper(b1)})", t1, y_pos)
    if b2: y_pos = yazdir_tutanak(f"2. KAT TUTANAĞI ({tr_upper(b2)})", t2, y_pos)
    if b3: y_pos = yazdir_tutanak(f"3. KAT TUTANAĞI ({tr_upper(b3)})", t3, y_pos)
    c.save(); b.seek(0); return b

def wp(tel, m):
    t = str(tel).replace(' ','').lstrip('0').replace('-','').replace('.','').strip()
    if not t or len(t) < 10: return None
    return f"https://wa.me/90{t}?text={urllib.parse.quote(m)}"

def sablon_indir():
    df_sablon = pd.DataFrame(columns=["Ad Soyad", "Numara", "Oda No", "Baba Adı", "Anne Adı", "Baba Tel", "Anne Tel"])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df_sablon.to_excel(writer, index=False)
    return output.getvalue()

# --- İŞLEMLER ---
def izn(i): st.session_state.df.at[i,"İzin Durumu"]="İzin Yok" if st.session_state.df.at[i,"İzin Durumu"]=="İzin Var" else "İzin Var"; kaydet()
def ey(i,t): st.session_state.df.at[i,t]={"⚪":"✅ Var","✅ Var":"❌ Yok","❌ Yok":"⚪"}.get(st.session_state.df.at[i,t],"⚪"); kaydet()
def msj(i,m): st.session_state.df.at[i,"Mesaj Durumu"]=m; kaydet()

# --- ARAYÜZ ---
c1, c2 = st.columns([3,1])
with c1: st.title("📱 Mobil Takip")
with c2: 
    if st.button("🔄"): st.cache_data.clear(); st.rerun()

menu = st.selectbox("Menü", ["📋 LİSTE", "📝 TUTANAK", "➕ EKLE", "🗑️ SİL", "🗄️ GEÇMİŞ", "📄 PDF"])

if menu == "📋 LİSTE":
    st.write(""); 
    if st.button("⚪ YENİ YOKLAMA BAŞLAT (Herkesi Sıfırla)", use_container_width=True): sifirla_yeni_yoklama()
    st.write("")
    
    c_kaydet, c_arsiv = st.columns(2)
    with c_kaydet: 
        if st.button("☁️ KAYDET (Manuel)", type="primary"): kaydet(); st.toast("Kaydedildi!")
    with c_arsiv:
        if st.button("🌙 GÜNÜ BİTİR"): arsivle()
        
    ara = st.text_input("🔍 Ara", placeholder="Öğrenci Adı veya Oda No...")
    f_df = st.session_state.df
    if ara: f_df = f_df[f_df.astype(str).apply(lambda x: x.str.contains(ara, case=False)).any(axis=1)]

    f_df["_Kat_Grubu"] = f_df["Oda No"].apply(kat_bul)
    kat_sirasi = ["1. KAT", "2. KAT", "3. KAT", "DİĞER"]
    st.info(f"Toplam: {len(f_df)} Öğrenci")

    for kat in kat_sirasi:
        kat_df = f_df[f_df["_Kat_Grubu"] == kat]
        if not kat_df.empty:
            with st.expander(f"🏢 {kat} ({len(kat_df)} Öğrenci)", expanded=False):
                renk = KAT_RENKLERI.get(kat, "#eee")
                st.markdown(f"""<div class="kat-baslik" style="background-color: {renk}; font-weight:bold;">{kat} LİSTESİ</div>""", unsafe_allow_html=True)
                odalar = sorted(kat_df["Oda No"].unique().tolist(), key=str)
                for oda in odalar:
                    st.markdown(f"##### 🛏️ Oda {oda}")
                    for i in kat_df[kat_df["Oda No"] == oda].index:
                        r = f_df.loc[i]
                        
                        # --- TİK OLUŞTURMA ALANI (GÜNCELLENDİ) ---
                        ikon = {"Yurtta": "🟢", "İzinli": "🟡", "Evde": "🔵", "Belirsiz": "⚪"}.get(r['Durum'], "⚪")
                        tikler = ""
                        
                        # Etüt veya Yat işaretliyse başlığa tik koy
                        if "Var" in str(r['Etüd']) or "Yok" in str(r['Etüd']): tikler += " [E✅]"
                        if "Var" in str(r['Yat']) or "Yok" in str(r['Yat']): tikler += " [Y✅]"
                        
                        with st.expander(f"{ikon} {r['Ad Soyad']} {tikler}"):
                            st.caption("Durum Seçiniz:")
                            secenekler = ["Yurtta", "İzinli", "Evde"]; 
                            if r['Durum'] == "Belirsiz": secenekler.insert(0, "Belirsiz")
                            try: m_idx = secenekler.index(r['Durum'])
                            except: m_idx = 0
                            yeni = st.radio("D", secenekler, index=m_idx, key=f"rd{i}", horizontal=True, label_visibility="collapsed")
                            if yeni != r['Durum']: st.session_state.df.at[i, "Durum"] = yeni; st.session_state.df.at[i, "Mesaj Durumu"] = "-"; kaydet(); st.rerun()
                            
                            if r['Durum'] == "Belirsiz": st.warning("⚠️ Seçiniz.")
                            elif r['Durum'] == "Yurtta":
                                st.divider(); c3, c4 = st.columns(2)
                                with c3:
                                    s = "primary" if "Yok" in str(r['Etüd']) else "secondary"
                                    if st.button(f"Etüd: {r['Etüd']}", key=f"e{i}", type=s, use_container_width=True): ey(i,"Etüd"); st.rerun()
                                with c4:
                                    s = "primary" if "Yok" in str(r['Yat']) else "secondary"
                                    if st.button(f"Yat: {r['Yat']}", key=f"y{i}", type=s, use_container_width=True): ey(i,"Yat"); st.rerun()
                                if "Yok" in str(r['Etüd']) or "Yok" in str(r['Yat']):
                                    st.warning("⚠️ Yoklamada Yok!"); msj_txt = f"Öğrenciniz {r['Ad Soyad']} etüd yoklamasına katılmamıştır." if "Yok" in str(r['Etüd']) else f"Öğrenciniz {r['Ad Soyad']} Yat yoklamasında yurtta bulunmamıştır."
                                    lb = wp(r['Baba Tel'], msj_txt); la = wp(r['Anne Tel'], msj_txt)
                                    if lb: st.link_button(f"👨 Baba", lb, use_container_width=True, type="primary")
                                    if la: st.link_button(f"👩 Anne", la, use_container_width=True, type="primary")
                                    if st.button("✅ Mesaj Atıldı", key=f"m{i}", use_container_width=True): msj(i, "Msj Atıldı"); st.rerun()
                            elif r['Durum'] == "Evde":
                                st.write(""); btn = "primary" if r['İzin Durumu']=="İzin Yok" else "secondary"; lbl = "✅ İzinli" if r['İzin Durumu']=="İzin Var" else "⛔ İzinsiz"
                                if st.button(lbl, key=f"i{i}", type=btn, use_container_width=True): izn(i); st.rerun()
                                if r['İzin Durumu'] == "İzin Var": st.success("Evci İzinli.")
                                else:
                                     st.error("🚨 KAÇAK!"); msj_txt = f"Öğrenciniz {r['Ad Soyad']} izinsiz olarak yurtta bulunmamaktadır."; lb = wp(r['Baba Tel'], msj_txt); la = wp(r['Anne Tel'], msj_txt)
                                     if lb: st.link_button("👨 Baba", lb, use_container_width=True, type="primary")
                                     if la: st.link_button("👩 Anne", la, use_container_width=True, type="primary")
                                     if st.button("✅ Ok", key=f"m{i}", use_container_width=True): msj(i, "Msj Atıldı"); st.rerun()
                            else: 
                                st.info("Çarşı İzinli"); s_yat = "primary" if "Yok" in str(r['Yat']) else "secondary"
                                if st.button(f"🛏️ Yat: {r['Yat']}", key=f"iy{i}", type=s_yat, use_container_width=True): ey(i,"Yat"); st.rerun()
                                if "Yok" in str(r['Yat']):
                                    st.warning("⚠️ Dönmedi!"); msj_txt = f"Öğrenciniz {r['Ad Soyad']} izinli olmasına rağmen Yat yoklamasında yurda giriş yapmamıştır."; lb = wp(r['Baba Tel'], msj_txt); la = wp(r['Anne Tel'], msj_txt)
                                    if lb: st.link_button("👨 Baba", lb, use_container_width=True, type="primary")
                                    if la: st.link_button("👩 Anne", la, use_container_width=True, type="primary")
                                    if st.button("✅ Ok", key=f"m{i}", use_container_width=True): msj(i, "Msj Atıldı"); st.rerun()

elif menu == "📝 TUTANAK":
    st.subheader("📝 Günlük Kat Tutanakları")
    st.session_state.tutanak_1 = st.text_area("1. Kat Tutanağı", st.session_state.tutanak_1, height=100)
    st.session_state.tutanak_2 = st.text_area("2. Kat Tutanağı", st.session_state.tutanak_2, height=100)
    st.session_state.tutanak_3 = st.text_area("3. Kat Tutanağı", st.session_state.tutanak_3, height=100)
    if st.button("💾 Tutanakları Kaydet", type="primary"): st.success("Kaydedildi")

elif menu == "➕ EKLE":
    st.subheader("Öğrenci Kayıt")
    tab1, tab2 = st.tabs(["✍️ Tek Tek Ekle", "📂 Excel Yükle"])
    with tab1:
        with st.form("ekle_manuel"):
            ad=st.text_input("Öğrenci Adı Soyadı")
            c1, c2 = st.columns(2); no=c1.text_input("Okul No"); oda=c2.text_input("Oda No")
            st.divider(); st.caption("Aile Bilgileri")
            b_ad = st.text_input("Baba Adı"); b_tel = st.text_input("Baba Tel"); a_ad = st.text_input("Anne Adı"); a_tel = st.text_input("Anne Tel")
            if st.form_submit_button("Kaydet", type="primary"):
                y = pd.DataFrame([{"Ad Soyad":ad, "Numara":no, "Oda No":oda, "Durum":"Belirsiz", "İzin Durumu":"İzin Var", "Etüd":"⚪", "Yat":"⚪", "Mesaj Durumu":"-", "Baba Adı":b_ad, "Anne Adı":a_ad, "Baba Tel":b_tel, "Anne Tel":a_tel}])
                st.session_state.df = pd.concat([st.session_state.df, y], ignore_index=True); kaydet(); st.success("Eklendi")
    with tab2:
        st.info("Gerekli: Ad Soyad, Numara, Oda No, Baba Adı, Anne Adı, Baba Tel, Anne Tel"); st.download_button("📥 Şablon", sablon_indir(), "sablon.xlsx")
        f = st.file_uploader("Excel Seç", type=["xlsx"])
        if f:
            try:
                ndf = pd.read_excel(f).astype(str)
                for c in SUTUNLAR: 
                    if c not in ndf.columns: ndf[c] = "-"
                ndf["Durum"]="Belirsiz"; ndf["İzin Durumu"]="İzin Var"; ndf["Etüd"]="⚪"; ndf["Yat"]="⚪"; ndf["Mesaj Durumu"]="-"
                ndf = ndf.replace("nan", "-")
                st.dataframe(ndf.head())
                if st.button("✅ Yükle", type="primary"):
                    st.session_state.df = pd.concat([st.session_state.df, ndf], ignore_index=True); kaydet(); st.success("Yüklendi!"); time.sleep(2); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

elif menu == "🗑️ SİL":
    st.subheader("🗑️ Öğrenci Silme Ekranı")
    st.warning("⚠️ DİKKAT: Buradan silinen öğrenci kalıcı olarak gider!")
    ara_sil = st.text_input("Silinecek Öğrenciyi Ara (Ad veya Oda No)")
    if ara_sil:
        silinecekler = st.session_state.df[st.session_state.df.astype(str).apply(lambda x: x.str.contains(ara_sil, case=False)).any(axis=1)]
        if not silinecekler.empty:
            st.write(f"{len(silinecekler)} sonuç bulundu:")
            for i in silinecekler.index:
                r = silinecekler.loc[i]
                with st.expander(f"❌ {r['Ad Soyad']} - {r['Oda No']}"):
                    st.write(f"Numara: {r['Numara']}")
                    if st.button("🗑️ BU ÖĞRENCİYİ SİL", key=f"sil_btn_{i}", type="primary"):
                        st.session_state.df = st.session_state.df.drop(i).reset_index(drop=True); kaydet(); st.success(f"{r['Ad Soyad']} silindi!"); time.sleep(1); st.rerun()
        else: st.info("Öğrenci bulunamadı.")

elif menu == "🗄️ GEÇMİŞ":
    try: d=pd.DataFrame(get_log().get_all_records()); st.dataframe(d[d["Tarih"]==st.selectbox("Tarih", d["Tarih"].unique())], use_container_width=True)
    except: st.info("Kayıt yok")

elif menu == "📄 PDF":
    st.subheader("PDF Raporu")
    st.info("Sadece ismini yazdığınız katların raporu oluşturulur.")
    c1, c2, c3 = st.columns(3)
    b1 = c1.text_input("1. Kat Belletmen")
    b2 = c2.text_input("2. Kat Belletmen")
    b3 = c3.text_input("3. Kat Belletmen")
    if st.button("PDF Oluştur", type="primary"):
        st.download_button("⬇️ İndir", pdf_yap(st.session_state.df, b1, b2, b3, st.session_state.tutanak_1, st.session_state.tutanak_2, st.session_state.tutanak_3), "yoklama.pdf", "application/pdf")
