import streamlit as st
import sqlite3
import io
import os
import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- TÜRKÇE FONT YÜKLEME VE KAYDETME ---
def turkce_fontlari_hazirla():
    font_dir = os.path.dirname(os.path.abspath(__file__))
    reg_path = os.path.join(font_dir, "DejaVuSans.ttf")
    bold_path = os.path.join(font_dir, "DejaVuSans-Bold.ttf")

    # Fontlar yoksa internet üzerinden otomatik indir
    if not os.path.exists(reg_path):
        try:
            url_reg = "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf"
            urllib.request.urlretrieve(url_reg, reg_path)
        except Exception:
            pass

    if not os.path.exists(bold_path):
        try:
            url_bold = "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans-Bold.ttf"
            urllib.request.urlretrieve(url_bold, bold_path)
        except Exception:
            pass

    # Fontları ReportLab sistemine kaydet
    try:
        if os.path.exists(reg_path) and os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont('DejaVuSans', reg_path))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_path))
            return 'DejaVuSans', 'DejaVuSans-Bold'
        elif os.path.exists('C:\\Windows\\Fonts\\arial.ttf') and os.path.exists('C:\\Windows\\Fonts\\arialbd.ttf'):
            pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
            return 'Arial', 'Arial-Bold'
    except Exception:
        pass

    return 'Helvetica', 'Helvetica-Bold'

FONT_REG, FONT_BOLD = turkce_fontlari_hazirla()

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont(FONT_REG, 9)
        self.setFillColor(colors.HexColor("#64748b"))
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 40, 559, 40)
        self.drawString(36, 25, "Mostech Grup Teknoloji - Teklif Dokümanı")
        page_str = f"Sayfa {self._pageNumber} / {page_count}"
        self.drawRightString(559, 25, page_str)
        self.restoreState()

DB_NAME = "stok_veritabani.db"

def vt_kur():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stok (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_kodu TEXT UNIQUE,
            urun_adi TEXT,
            kategori TEXT,
            stok_adet REAL,
            fiyat_usd REAL,
            kritik_seviye REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cariler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unvan TEXT UNIQUE,
            yetkili TEXT,
            telefon TEXT,
            eposta TEXT,
            adres TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cari_hareketler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cari_id INTEGER,
            tarih TEXT,
            islem_turu TEXT,
            aciklama TEXT,
            tutar REAL,
            para_birimi TEXT,
            FOREIGN KEY(cari_id) REFERENCES cariler(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kasa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            islem_turu TEXT,
            aciklama TEXT,
            tutar REAL,
            para_birimi TEXT,
            cari_id INTEGER NULL,
            FOREIGN KEY(cari_id) REFERENCES cariler(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_adi TEXT UNIQUE,
            sifre TEXT
        )
    """)
    
    # İlk varsayılan kullanıcı kontrolü
    cursor.execute("SELECT COUNT(*) FROM kullanicilar")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)", ("mostech", "Eelsan21."))
        
    conn.commit()
    conn.close()

vt_kur()

# --- GİRİŞ KONTROLÜ (AUTHENTICATION) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.authenticated:
    st.set_page_config(page_title="Giriş - Mostech ERP Web", page_icon="🔒", layout="centered")
    
    if os.path.exists("logo.png"):
        st.image("logo.png", width=220)
    st.title("🔒 Mostech ERP - Giriş Ekranı")
    
    with st.form("login_form"):
        user_input = st.text_input("Kullanıcı Adı")
        pass_input = st.text_input("Şifre", type="password")
        submit = st.form_submit_button("Giriş Yap", use_container_width=True)
        
        if submit:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi=? AND sifre=?", (user_input, pass_input))
            user_record = cursor.fetchone()
            conn.close()
            
            if user_record:
                st.session_state.authenticated = True
                st.session_state.user = user_input
                st.success("Giriş başarılı!")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

# --- ANA UYGULAMA DÖNGÜSÜ ---
def tcmb_kuru_cek():
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        for currency in root.findall('Currency'):
            if currency.get('Kod') == 'USD':
                kur_str = currency.find('ForexSelling').text or currency.find('BanknoteSelling').text
                if kur_str:
                    return float(kur_str.replace(',', '.'))
    except Exception:
        return 48.00
    return 48.00

def pdf_uret_buffer(musteri_adi, kur, para_birimi, kalemler, logo_path="logo.png"):
    buffer = io.BytesIO()
    is_tl = "TRY" in para_birimi
    toplam_usd = sum(k["toplam"] for k in kalemler)
    ara_toplam_tl = toplam_usd * kur
    kdv_tl = ara_toplam_tl * 0.20
    genel_toplam_tl = ara_toplam_tl + kdv_tl

    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=54)
    story = []
    styles = getSampleStyleSheet()

    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=15, leading=18, textColor=colors.HexColor('#be123c'), alignment=2)
    text_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontName=FONT_REG, fontSize=9, leading=13, textColor=colors.HexColor('#334155'))
    bold_text = ParagraphStyle('BodyTextBold', parent=text_style, fontName=FONT_BOLD)
    header_cell_style = ParagraphStyle('HeaderCell', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=9, leading=12, textColor=colors.white)
    cell_style = ParagraphStyle('CellText', parent=styles['Normal'], fontName=FONT_REG, fontSize=9, leading=12, textColor=colors.HexColor('#1e293b'))
    cell_style_right = ParagraphStyle('CellTextRight', parent=cell_style, alignment=2)
    cell_style_center = ParagraphStyle('CellTextCenter', parent=cell_style, alignment=1)

    logo_element = RLImage(logo_path, width=150, height=45) if os.path.exists(logo_path) else Paragraph("<b>MOSTECH GRUP TEKNOLOJİ</b>", ParagraphStyle('TF', fontName=FONT_BOLD, fontSize=14))

    sirket_bilgi_metni = (
        "<b>MOSTECH GRUP TEKNOLOJİ</b><br/>"
        "Adres: Muratpaşa Mah. Saraybosna Cad. Sabunhane Sok. 4/B Yakutiye / Erzurum<br/>"
        "Tel: 0442 215 7 777 | GSM: 0534 704 40 73<br/>"
        "Web: www.mostechgrup.com | E-posta: info@mostechgrup.com"
    )

    header_table = Table([[logo_element, Paragraph("TEKLİF FORMU", subtitle_style)],
                           [Paragraph(sirket_bilgi_metni, text_style), Paragraph("<b>Tarih:</b> 31.08.2026", ParagraphStyle('R', parent=text_style, alignment=2))]], colWidths=[310, 213])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(header_table); story.append(Spacer(1, 15))

    info_data = [
        [Paragraph("<b>MÜŞTERİ BİLGİLERİ</b>", bold_text), Paragraph("<b>TEKLİF DETAYLARI</b>", bold_text)],
        [Paragraph(f"<b>Firma / Müşteri:</b> {musteri_adi}", text_style), Paragraph(f"<b>Dolar Kuru (USD/TRY):</b> ₺{kur:.4f}", text_style)],
        [Paragraph("<b>Hizmet Türü:</b> Güvenlik & Teknoloji Sistemleri", text_style), Paragraph(f"<b>Teklif Para Birimi:</b> {para_birimi}", text_style)]
    ]
    info_table = Table(info_data, colWidths=[260, 263])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(info_table); story.append(Spacer(1, 15))

    birim_baslik = "Birim Fiyat (TL)" if is_tl else "Birim Fiyat ($)"
    toplam_baslik = "Toplam (TL)" if is_tl else "Toplam ($)"

    table_data = [[
        Paragraph("No", header_cell_style),
        Paragraph("Ürün / Hizmet Açıklaması", header_cell_style),
        Paragraph("Miktar", ParagraphStyle('HC', parent=header_cell_style, alignment=1)),
        Paragraph(birim_baslik, ParagraphStyle('HR', parent=header_cell_style, alignment=2)),
        Paragraph(toplam_baslik, ParagraphStyle('HR2', parent=header_cell_style, alignment=2))
    ]]

    for i, item in enumerate(kalemler, 1):
        if is_tl:
            bf = item["fiyat"] * kur
            tf = item["toplam"] * kur
            str_bf = f"₺{bf:,.2f}"
            str_tf = f"₺{tf:,.2f}"
        else:
            str_bf = f"${item['fiyat']:.2f}"
            str_tf = f"${item['toplam']:.2f}"

        table_data.append([
            Paragraph(str(i), cell_style_center),
            Paragraph(item["urun"], cell_style),
            Paragraph(f"{item['miktar']:g}", cell_style_center),
            Paragraph(str_bf, cell_style_right),
            Paragraph(str_tf, cell_style_right)
        ])

    items_table = Table(table_data, colWidths=[30, 263, 60, 85, 85])
    ts = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ])
    for r in range(1, len(table_data)):
        if r % 2 == 0: ts.add('BACKGROUND', (0, r), (-1, r), colors.HexColor('#f8fafc'))
    items_table.setStyle(ts); story.append(items_table); story.append(Spacer(1, 15))

    if is_tl:
        totals_data = [
            [Paragraph("<b>Ara Toplam (TL):</b>", text_style), Paragraph(f"₺{ara_toplam_tl:,.2f}", cell_style_right)],
            [Paragraph("<b>KDV (%20):</b>", text_style), Paragraph(f"₺{kdv_tl:,.2f}", cell_style_right)],
            [Paragraph("<b>GENEL TOPLAM:</b>", ParagraphStyle('GT', parent=bold_text, fontSize=11, textColor=colors.HexColor('#991b1b'))), 
             Paragraph(f"<b>₺{genel_toplam_tl:,.2f}</b>", ParagraphStyle('GTR', parent=cell_style_right, fontSize=11, fontName=FONT_BOLD, textColor=colors.HexColor('#991b1b')))]
        ]
    else:
        kdv_usd = toplam_usd * 0.20
        genel_usd = toplam_usd + kdv_usd
        totals_data = [
            [Paragraph("<b>Ara Toplam (USD):</b>", text_style), Paragraph(f"${toplam_usd:,.2f}", cell_style_right)],
            [Paragraph("<b>KDV (%20 USD):</b>", text_style), Paragraph(f"${kdv_usd:,.2f}", cell_style_right)],
            [Paragraph("<b>Ara Toplam (TL Karşılığı):</b>", text_style), Paragraph(f"₺{ara_toplam_tl:,.2f}", cell_style_right)],
            [Paragraph("<b>GENEL TOPLAM (USD):</b>", ParagraphStyle('GT', parent=bold_text, fontSize=11, textColor=colors.HexColor('#991b1b'))), 
             Paragraph(f"<b>${genel_usd:,.2f}</b>", ParagraphStyle('GTR', parent=cell_style_right, fontSize=11, fontName=FONT_BOLD, textColor=colors.HexColor('#991b1b')))],
            [Paragraph("<b>GENEL TOPLAM (TL):</b>", ParagraphStyle('GT2', parent=bold_text, fontSize=10, textColor=colors.HexColor('#0f172a'))), 
             Paragraph(f"<b>₺{genel_toplam_tl:,.2f}</b>", ParagraphStyle('GTR2', parent=cell_style_right, fontSize=10, fontName=FONT_BOLD, textColor=colors.HexColor('#0f172a')))]
        ]

    totals_table = Table(totals_data, colWidths=[200, 120])
    totals_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f1f5f9')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0,-2), (-1,-2), 1.5, colors.HexColor('#991b1b')),
    ]))

    wrapper_table = Table([[Paragraph("", text_style), totals_table]], colWidths=[203, 320])
    wrapper_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    story.append(wrapper_table); story.append(Spacer(1, 20))

    terms_data = [
        [Paragraph("<b>TEKLİF ŞARTLARI VE ŞARTNAME</b>", bold_text)],
        [Paragraph("1. Fiyatlara %20 KDV dahil edilerek genel toplam hesaplanmıştır.<br/>"
                   "2. Teklif tarihi itibarıyla geçerli TCMB USD satış kuru esas alınmıştır.<br/>"
                   "3. Bu teklif hazırlandığı tarihten itibaren 15 (on beş) gün süreyle geçerlidir.<br/>"
                   "4. Ödeme iş bitiminde güncel kur üzerinden yapılacaktır.<br/>"
                   "5. İmalattan kaynaklanan arızalar için ürünler 2 yıl garantilidir.", text_style)]
    ]
    terms_table = Table(terms_data, colWidths=[523])
    terms_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fafafa')), ('PADDING', (0,0), (-1,-1), 8), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0'))]))
    story.append(terms_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()

st.set_page_config(page_title="Mostech ERP Web", layout="wide")

# Sidebar Kullanıcı Bilgisi & Çıkış
st.sidebar.markdown(f"**Aktif Kullanıcı:** `{st.session_state.user}`")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

col_logo, col_head = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=180)
with col_head:
    st.title("MOSTECH GRUP TEKNOLOJİ")
    st.caption("Adres: Muratpaşa Mah. Saraybosna Cad. Sabunhane Sok. 4/B Yakutiye / Erzurum | Tel: 0442 215 7 777")

if "kalemler" not in st.session_state:
    st.session_state.kalemler = []
if "guncel_kur" not in st.session_state:
    st.session_state.guncel_kur = tcmb_kuru_cek()

tab_teklif, tab_stok, tab_cari, tab_kasa, tab_sifre = st.tabs([
    "Teklif Hazırlama", "Stok Yönetimi", "Cari & Hesap Yönetimi", "Kasa Gelir/Gider", "⚙️ Şifre Değiştir"
])

# ================= 1. TEKLİF HAZIRLAMA =================
with tab_teklif:
    st.subheader("Teklif ve Kur Parametreleri")
    
    conn = sqlite3.connect(DB_NAME)
    cariler_db = conn.execute("SELECT unvan FROM cariler").fetchall()
    conn.close()
    cari_unvanlar = [c[0] for c in cariler_db]
    
    col_c1, col_c2, col_c3, col_c4 = st.columns([2, 2, 1, 1])
    secilen_cari = col_c1.selectbox("Cari Müşteri Seç", ["- Manuel Gir -"] + cari_unvanlar)
    musteri_input = col_c2.text_input("Müşteri / Firma Adı", value="" if secilen_cari == "- Manuel Gir -" else secilen_cari)
    para_birimi = col_c3.selectbox("Teklif Para Birimi", ["USD ($)", "TRY (₺)"])
    kur = col_c4.number_input("USD/TRY Kuru", value=st.session_state.guncel_kur, format="%.4f")
    
    if st.button("TCMB Kuru Güncelle"):
        st.session_state.guncel_kur = tcmb_kuru_cek()
        st.rerun()

    st.divider()
    st.subheader("Stoktan veya Manuel Ürün Ekle")
    
    conn = sqlite3.connect(DB_NAME)
    stoklar_db = conn.execute("SELECT urun_kodu, urun_adi, fiyat_usd FROM stok").fetchall()
    conn.close()
    stok_map = {f"{s[0]} - {s[1]}": s for s in stoklar_db}
    
    secilen_stok_key = st.selectbox("Stoktan Ürün Seç (Opsiyonel)", ["- Manuel Giriş -"] + list(stok_map.keys()))
    
    stok_default_adi = ""
    stok_default_fiyat = 0.0
    if secilen_stok_key != "- Manuel Giriş -":
        stok_default_adi = stok_map[secilen_stok_key][1]
        stok_default_fiyat = float(stok_map[secilen_stok_key][2])

    with st.form("kalem_ekle_form"):
        fk1, fk2, fk3 = st.columns([3, 1, 1])
        u_adi = fk1.text_input("Ürün / Hizmet Açıklaması", value=stok_default_adi)
        u_mikt = fk2.number_input("Miktar", min_value=1.0, value=1.0)
        u_fiyat = fk3.number_input("Birim Fiyat ($)", min_value=0.0, value=stok_default_fiyat)
        
        if st.form_submit_button("Listeye Ekle") and u_adi:
            st.session_state.kalemler.append({
                "urun": u_adi, "miktar": u_mikt, "fiyat": u_fiyat, "toplam": u_mikt * u_fiyat
            })
            st.success("Kalem teklif listesine eklendi.")
            st.rerun()

    if st.session_state.kalemler:
        st.write("### Teklif Kalemleri")
        df_kalemler = pd.DataFrame(st.session_state.kalemler)
        st.dataframe(df_kalemler, use_container_width=True)
        
        toplam_usd = sum(k["toplam"] for k in st.session_state.kalemler)
        ara_toplam_tl = toplam_usd * kur
        kdv_tl = ara_toplam_tl * 0.20
        genel_toplam_tl = ara_toplam_tl + kdv_tl
        
        if "TRY" in para_birimi:
            st.info(f"**Ara Toplam:** ₺{ara_toplam_tl:,.2f} | **KDV (%20):** ₺{kdv_tl:,.2f} | **GENEL TOPLAM:** ₺{genel_toplam_tl:,.2f}")
        else:
            st.info(f"**Ara Toplam:** ${toplam_usd:,.2f} (₺{ara_toplam_tl:,.2f}) | **KDV:** ₺{kdv_tl:,.2f} | **GENEL TOPLAM:** ₺{genel_toplam_tl:,.2f}")

        col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
        if col_b1.button("Listeyi Temizle"):
            st.session_state.kalemler = []
            st.rerun()

        pdf_bytes = pdf_uret_buffer(musteri_input or "Musteri", kur, para_birimi, st.session_state.kalemler)
        col_b2.download_button(
            label="📥 PDF Teklifi Oluştur ve İndir",
            data=pdf_bytes,
            file_name=f"Teklif_{musteri_input.replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        if col_b3.button("Stoktan Düş"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            for k in st.session_state.kalemler:
                cursor.execute("UPDATE stok SET stok_adet = stok_adet - ? WHERE urun_adi = ?", (k["miktar"], k["urun"]))
            conn.commit()
            conn.close()
            st.success("Ürün miktarları stoktan düşüldü.")

# ================= 2. STOK YÖNETİMİ =================
with tab_stok:
    st.subheader("Stok Ürün Ekle / Güncelle")
    with st.form("stok_form"):
        sc1, sc2, sc3 = st.columns(3)
        kod = sc1.text_input("Ürün Kodu")
        ad = sc2.text_input("Ürün Adı")
        kat = sc3.text_input("Kategori")
        sc4, sc5, sc6 = st.columns(3)
        adet = sc4.number_input("Stok Miktarı", value=0.0)
        fiyat = sc5.number_input("Birim Fiyat ($)", value=0.0)
        kritik = sc6.number_input("Kritik Limit", value=5.0)
        
        if st.form_submit_button("Stoka Kaydet / Güncelle"):
            if kod and ad:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO stok (urun_kodu, urun_adi, kategori, stok_adet, fiyat_usd, kritik_seviye)
                    VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(urun_kodu) DO UPDATE SET
                    urun_adi=excluded.urun_adi, kategori=excluded.kategori, stok_adet=excluded.stok_adet,
                    fiyat_usd=excluded.fiyat_usd, kritik_seviye=excluded.kritik_seviye
                """, (kod, ad, kat, adet, fiyat, kritik))
                conn.commit()
                conn.close()
                st.success("Stok kaydı güncellendi.")
                st.rerun()

    st.divider()
    st.subheader("Stok Listesi")
    conn = sqlite3.connect(DB_NAME)
    stok_df = pd.read_sql_query("SELECT id, urun_kodu, urun_adi, kategori, stok_adet, fiyat_usd, kritik_seviye FROM stok", conn)
    conn.close()
    
    if not stok_df.empty:
        st.dataframe(stok_df, use_container_width=True)
        col_s1, col_s2 = st.columns([1, 3])
        sil_id = col_s1.number_input("Silinecek Stok ID", min_value=1, step=1)
        if col_s2.button("Seçili Stoğu Sil"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM stok WHERE id=?", (sil_id,))
            conn.commit()
            conn.close()
            st.success(f"ID: {sil_id} stok silindi.")
            st.rerun()

# ================= 3. CARİ & HESAP YÖNETİMİ =================
with tab_cari:
    st.subheader("Müşteri Cari Kaydı")
    with st.form("cari_form"):
        cc1, cc2, cc3 = st.columns(3)
        unvan = cc1.text_input("Firma / Ünvan")
        yetkili = cc2.text_input("Yetkili Kişi")
        tel = cc3.text_input("Telefon")
        cc4, cc5 = st.columns([1, 2])
        eposta = cc4.text_input("E-Posta")
        adres = cc5.text_input("Adres")
        
        if st.form_submit_button("Cari Kaydet / Güncelle"):
            if unvan:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO cariler (unvan, yetkili, telefon, eposta, adres)
                    VALUES (?, ?, ?, ?, ?) ON CONFLICT(unvan) DO UPDATE SET
                    yetkili=excluded.yetkili, telefon=excluded.telefon,
                    eposta=excluded.eposta, adres=excluded.adres
                """, (unvan, yetkili, tel, eposta, adres))
                conn.commit()
                conn.close()
                st.success("Cari kayıt güncellendi.")
                st.rerun()

    st.divider()
    st.subheader("Cari Borç / Alacak İşlemi")
    conn = sqlite3.connect(DB_NAME)
    cariler_list = conn.execute("SELECT id, unvan FROM cariler").fetchall()
    conn.close()
    cari_dict = {f"{c[0]} - {c[1]}": c[0] for c in cariler_list}

    if cari_dict:
        secilen_cari_combo = st.selectbox("İşlem Yapılacak Cariyi Seçin", list(cari_dict.keys()))
        secili_cari_id = cari_dict[secilen_cari_combo]

        with st.form("cari_har_form"):
            hc1, hc2, hc3, hc4 = st.columns(4)
            h_tarih = hc1.text_input("Tarih", value="31.08.2026")
            h_tur = hc2.selectbox("İşlem Türü", ["Borç (Satış/Alacaklandır)", "Alacak (Ödeme Alma/Tahsilat)"])
            h_tutar = hc3.number_input("Tutar", min_value=0.0)
            h_birim = hc4.selectbox("Para Birimi", ["TRY (₺)", "USD ($)"])
            h_aciklama = st.text_input("Açıklama")

            if st.form_submit_button("İşlemi Cari Hesaba İşle"):
                if h_tutar > 0:
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("""
                        INSERT INTO cari_hareketler (cari_id, tarih, islem_turu, aciklama, tutar, para_birimi)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (secili_cari_id, h_tarih, h_tur, h_aciklama, h_tutar, h_birim))
                    conn.commit()
                    conn.close()
                    st.success("Cari işlem kaydedildi.")
                    st.rerun()

    st.divider()
    st.subheader("Cari Bakiye Durumları")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, unvan, yetkili, telefon, eposta, adres FROM cariler")
    cariler_raw = cursor.fetchall()

    cariler_display = []
    for r in cariler_raw:
        c_id, c_unvan, c_yetkili, c_tel, c_eposta, c_adres = r
        cursor.execute("SELECT islem_turu, tutar, para_birimi FROM cari_hareketler WHERE cari_id=?", (c_id,))
        h_rows = cursor.fetchall()
        
        bakiye_tl = 0.0
        bakiye_usd = 0.0
        for h in h_rows:
            tur, tutar, birim = h[0], h[1], h[2]
            carpan = 1 if "Borç" in tur else -1
            if "TRY" in birim:
                bakiye_tl += (tutar * carpan)
            else:
                bakiye_usd += (tutar * carpan)
                
        cariler_display.append({
            "ID": c_id,
            "Firma / Ünvan": c_unvan,
            "Yetkili": c_yetkili,
            "Telefon": c_tel,
            "E-Posta": c_eposta,
            "Bakiye (TL)": f"₺{bakiye_tl:,.2f}",
            "Bakiye ($)": f"${bakiye_usd:,.2f}"
        })

    if cariler_display:
        st.dataframe(pd.DataFrame(cariler_display), use_container_width=True)
        
        if cari_dict:
            st.write("### Seçili Cariye Ait İşlem Geçmişi")
            gecmis_df = pd.read_sql_query(
                "SELECT id, tarih, islem_turu, aciklama, tutar, para_birimi FROM cari_hareketler WHERE cari_id=? ORDER BY id DESC",
                conn, params=(secili_cari_id,)
            )
            if not gecmis_df.empty:
                st.dataframe(gecmis_df, use_container_width=True)
            else:
                st.info("Bu cariye ait henüz işlem geçmişi bulunmuyor.")
    conn.close()

# ================= 4. KASA GELİR / GİDER =================
with tab_kasa:
    st.subheader("Kasa İşlemi Ekle")
    conn = sqlite3.connect(DB_NAME)
    cariler_list_kasa = conn.execute("SELECT id, unvan FROM cariler").fetchall()
    conn.close()
    kasa_cari_dict = {"- İlişkisiz -": None}
    for c in cariler_list_kasa:
        kasa_cari_dict[f"{c[0]} - {c[1]}"] = c[0]

    with st.form("kasa_form"):
        kc1, kc2, kc3, kc4 = st.columns(4)
        k_tarih = kc1.text_input("Tarih", value="31.08.2026")
        k_tur = kc2.selectbox("İşlem Türü", ["Tahsilat (Gelir)", "Ödeme (Gider)"])
        k_tutar = kc3.number_input("Tutar", min_value=0.0)
        k_birim = kc4.selectbox("Birim", ["TRY (₺)", "USD ($)"])
        
        kc5, kc6 = st.columns([2, 1])
        k_aciklama = kc5.text_input("Açıklama")
        k_cari_sec = kc6.selectbox("İlişkili Cari (Opsiyonel)", list(kasa_cari_dict.keys()))

        if st.form_submit_button("Kasa İşlemini Kaydet"):
            if k_tutar > 0:
                rel_cari_id = kasa_cari_dict[k_cari_sec]
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO kasa (tarih, islem_turu, aciklama, tutar, para_birimi, cari_id) VALUES (?, ?, ?, ?, ?, ?)",
                               (k_tarih, k_tur, k_aciklama, k_tutar, k_birim, rel_cari_id))
                
                if rel_cari_id:
                    cari_tur = "Alacak (Ödeme Alma/Tahsilat)" if "Tahsilat" in k_tur else "Borç (Satış/Alacaklandır)"
                    cursor.execute("""
                        INSERT INTO cari_hareketler (cari_id, tarih, islem_turu, aciklama, tutar, para_birimi)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (rel_cari_id, k_tarih, cari_tur, f"Kasa İşlemi: {k_aciklama}", k_tutar, k_birim))
                    
                conn.commit()
                conn.close()
                st.success("Kasa işlemi kaydedildi.")
                st.rerun()

    st.divider()
    st.subheader("Kasa Hareketleri ve Bakiye Özeti")
    
    conn = sqlite3.connect(DB_NAME)
    kasa_rows = conn.execute("""
        SELECT k.id, k.tarih, k.islem_turu, c.unvan, k.aciklama, k.tutar, k.para_birimi 
        FROM kasa k LEFT JOIN cariler c ON k.cari_id = c.id ORDER BY k.id DESC
    """).fetchall()
    conn.close()

    toplam_gelir_tl = 0.0
    toplam_gider_tl = 0.0
    kur_val = st.session_state.guncel_kur

    kasa_list = []
    for r in kasa_rows:
        k_id, k_tarih, k_tur, c_unvan, k_aciklama, k_tutar, k_birim = r
        tutar_tl = k_tutar if "TRY" in k_birim else k_tutar * kur_val
        if "Tahsilat" in k_tur:
            toplam_gelir_tl += tutar_tl
        else:
            toplam_gider_tl += tutar_tl
            
        kasa_list.append({
            "ID": k_id,
            "Tarih": k_tarih,
            "İşlem Türü": k_tur,
            "İlişkili Cari": c_unvan or "-",
            "Açıklama": k_aciklama,
            "Tutar": f"{k_tutar:,.2f}",
            "Birim": k_birim
        })

    net_bakiye_tl = toplam_gelir_tl - toplam_gider_tl

    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Gelir (TL)", f"₺{toplam_gelir_tl:,.2f}")
    m2.metric("Toplam Gider (TL)", f"₺{toplam_gider_tl:,.2f}")
    m3.metric("Net Kasa Bakiyesi (TL)", f"₺{net_bakiye_tl:,.2f}")

    st.write("---")
    if kasa_list:
        st.dataframe(pd.DataFrame(kasa_list), use_container_width=True)
        
        col_k1, col_k2 = st.columns([1, 3])
        sil_kasa_id = col_k1.number_input("Silinecek Kasa ID", min_value=1, step=1)
        if col_k2.button("Seçili Kasa Hareketini Sil"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM kasa WHERE id=?", (sil_kasa_id,))
            conn.commit()
            conn.close()
            st.success(f"ID: {sil_kasa_id} kasa hareketi silindi.")
            st.rerun()

# ================= 5. YÖNETİCİ ŞİFRE DEĞİŞTİRME =================
with tab_sifre:
    st.subheader("Yönetici Şifre Değiştirme Paneli")
    
    with st.form("sifre_degistir_form"):
        mevcut_sifre = st.text_input("Mevcut Şifre", type="password")
        yeni_sifre = st.text_input("Yeni Şifre", type="password")
        yeni_sifre_tekrar = st.text_input("Yeni Şifre (Tekrar)", type="password")
        
        if st.form_submit_button("Şifreyi Güncelle"):
            if yeni_sifre != yeni_sifre_tekrar:
                st.error("Yeni şifreler birbiriyle eşleşmiyor!")
            elif not yeni_sifre.strip():
                st.error("Yeni şifre alanı boş bırakılamaz!")
            else:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi=? AND sifre=?", (st.session_state.user, mevcut_sifre))
                user_rec = cursor.fetchone()
                
                if user_rec:
                    cursor.execute("UPDATE kullanicilar SET sifre=? WHERE kullanici_adi=?", (yeni_sifre, st.session_state.user))
                    conn.commit()
                    st.success("Yönetici şifresi başarıyla değiştirildi! Bir sonraki girişte yeni şifreniz geçerli olacaktır.")
                else:
                    st.error("Mevcut şifreniz hatalı!")
                conn.close()
