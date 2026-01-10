from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import pg8000.native
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse
from hashlib import sha256
import secrets
import random

app = Flask(__name__)
app.secret_key = 'swing-planet-2024-secret-key'
app.config['JSON_AS_ASCII'] = False  # Türkçe karakterler için
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=90)  # 3 ay hatırla

DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_db():
    parsed = urlparse(DATABASE_URL)
    conn = pg8000.native.Connection(
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:]
    )
    return conn

def init_db():
    conn = get_db()
    conn.run('''
        CREATE TABLE IF NOT EXISTS rezervasyonlar (
            id SERIAL PRIMARY KEY,
            studyo TEXT NOT NULL,
            alan TEXT NOT NULL,
            tarih DATE NOT NULL,
            saat TEXT NOT NULL,
            rezerve_eden TEXT,
            telefon TEXT,
            bloklu BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(studyo, alan, tarih, saat)
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS aktiviteler (
            id SERIAL PRIMARY KEY,
            isim TEXT NOT NULL,
            islem TEXT NOT NULL,
            studyo TEXT NOT NULL,
            alan TEXT NOT NULL,
            tarih DATE NOT NULL,
            saat TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS pratik_anket (
            id SERIAL PRIMARY KEY,
            pratik_tarih DATE NOT NULL,
            lokasyon TEXT NOT NULL,
            telefon TEXT NOT NULL,
            isim TEXT NOT NULL,
            cevap TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pratik_tarih, lokasyon, telefon)
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS pratik_gorevli (
            id SERIAL PRIMARY KEY,
            pratik_tarih DATE NOT NULL,
            lokasyon TEXT NOT NULL,
            telefon TEXT NOT NULL,
            isim TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pratik_tarih, lokasyon, telefon)
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS kullanici_sifreler (
            id SERIAL PRIMARY KEY,
            telefon TEXT UNIQUE NOT NULL,
            sifre_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS giris_denemeleri (
            id SERIAL PRIMARY KEY,
            telefon TEXT NOT NULL,
            ip_adresi TEXT,
            basarili BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Görev Takip Tabloları
    conn.run('''
        CREATE TABLE IF NOT EXISTS gorevler (
            id SERIAL PRIMARY KEY,
            baslik TEXT NOT NULL,
            durum TEXT DEFAULT 'bekliyor',
            olusturan TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS gorev_notlar (
            id SERIAL PRIMARY KEY,
            gorev_id INTEGER REFERENCES gorevler(id) ON DELETE CASCADE,
            yazar TEXT NOT NULL,
            yazar_isim TEXT NOT NULL,
            not_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.close()

try:
    init_db()
except:
    pass

KULLANICILAR = {
    # Admin'ler
    "5554128946": {"isim": "Uğur Altun", "admin": True},
    "5302605898": {"isim": "Bilge Sağnak Altun", "admin": True},
    
    # Ekip
    "5409171998": {"isim": "Kübra Gözde Zorlu", "admin": False},
    "5347666377": {"isim": "Berfin Tomruk", "admin": False},
    "5074942445": {"isim": "Özhan Kakış", "admin": False},
    "5367194693": {"isim": "Mert Tomruk", "admin": False},
    "5417383748": {"isim": "Duygu Bölükbaşı Yıldırım", "admin": False},
    "5364906694": {"isim": "Ceyhan İleri", "admin": False},
    "5425614963": {"isim": "Büşra Karaköse", "admin": False},
    "5307013845": {"isim": "Tuğçe Karagülen", "admin": False},
    "5434564332": {"isim": "Enes Çepni", "admin": False},
    "5377974644": {"isim": "Serpil Koşak", "admin": False},
    "5357132619": {"isim": "Alperen Hacıismailoğlu", "admin": False},
    "5448482424": {"isim": "Zehra Ergül", "admin": False},
    "5348878568": {"isim": "Muhammet Bülbül", "admin": False},
    "5350279213": {"isim": "Emre Ağdaş", "admin": False},
    "5335437664": {"isim": "İlker Güney", "admin": False},
    "5302821881": {"isim": "Kayhan Tüfekçi", "admin": False},
    "5367777965": {"isim": "Başak Cengiz", "admin": False},
    "5455151266": {"isim": "Atacan Ağüzüm", "admin": False},
    "5528451111": {"isim": "Emre Gökalp", "admin": False},
    "5064568591": {"isim": "Funda Açlan", "admin": False},
    "5383537044": {"isim": "Nida Küçükaslan", "admin": False},
    "5075277754": {"isim": "Zehra Erek", "admin": False},
    "5050230175": {"isim": "Beyza Yıldırım", "admin": False},
    "5066735330": {"isim": "Özge Aydın", "admin": False},
    "5068647964": {"isim": "Ceyda Dinç", "admin": False},
    "5397834846": {"isim": "Büşra Aydoğanoğlu", "admin": False},
    "5445360312": {"isim": "Leyla Özler", "admin": False},
    "5465358679": {"isim": "Büşra Gül", "admin": False},
    "5333737400": {"isim": "Burçin Torun", "admin": False},
    "5434849161": {"isim": "Elif Atmaca", "admin": False},
    "5543898154": {"isim": "Mehmet Yıldırım", "admin": False},
    "5057710492": {"isim": "Ahmet Kızgın", "admin": False},
    "5357717101": {"isim": "Süleyman Ufuk Eroğlu", "admin": False},
    "5071299465": {"isim": "Onur Özdemir", "admin": False},
    "5306653496": {"isim": "Erdem Eren", "admin": False},
    "5317705515": {"isim": "Deniz Temizkan", "admin": False},
    "5319478065": {"isim": "Sueda Yüceer", "admin": False},
    "5312103619": {"isim": "Melike Gün", "admin": False},
    "5334187526": {"isim": "Ezgi Tan", "admin": False},
    "5052399493": {"isim": "Atalay Okun", "admin": False},
    "5352041658": {"isim": "Mustafa Kemal Doğançay", "admin": False},
}

# Görev Takip - Sadece bu kişiler erişebilir
GOREV_ERISIM = {
    "5554128946": "admin",      # Uğur Altun
    "5352041658": "kullanici",  # Mustafa Kemal Doğançay
}

STUDYOLAR = {
    'kadikoy': {
        'isim': 'Kadıköy',
        'alanlar': ['Ana Salon'],
        'saatler': {
            'hafta_ici': {'baslangic': '16:00', 'bitis': '22:00'},
            'hafta_sonu': {'baslangic': '12:00', 'bitis': '22:00'}
        }
    },
    'sisli': {
        'isim': 'Şişli',
        'alanlar': ['Büyük Stüdyo', 'Küçük Stüdyo', 'Perdeli Alan'],
        'saatler': {
            'hafta_ici': {'baslangic': '12:00', 'bitis': '22:00'},
            'hafta_sonu': {'baslangic': '12:00', 'bitis': '22:00'}
        }
    }
}

PRATIK_BILGI = {
    'sisli': {
        'gun': 2,  # Çarşamba
        'saat': '20.30 - 22.30',
        'yer': 'Şişli Bomonti'
    },
    'kadikoy': {
        'gun': 4,  # Cuma
        'saat': '20.45 - 22.30',
        'yer': 'Kadıköy'
    }
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'telefon' not in session:
            return redirect(url_for('giris'))
        return f(*args, **kwargs)
    return decorated_function

def hash_sifre(sifre):
    """Şifreyi güvenli şekilde hashle"""
    return sha256((sifre + 'swing-planet-salt-2024').encode()).hexdigest()

def sifre_dogrula(sifre, sifre_hash):
    """Şifreyi hash ile karşılaştır"""
    return hash_sifre(sifre) == sifre_hash

def kullanici_kilitli_mi(telefon):
    """Son 15 dakikada 5+ başarısız deneme varsa kilitle"""
    try:
        conn = get_db()
        rows = conn.run('''
            SELECT COUNT(*) FROM giris_denemeleri 
            WHERE telefon = :p1 
            AND basarili = FALSE 
            AND created_at > :p2
        ''', p1=telefon, p2=(datetime.now() - timedelta(minutes=15)).isoformat())
        conn.close()
        return rows[0][0] >= 5
    except:
        return False

def giris_denemesi_kaydet(telefon, ip_adresi, basarili):
    """Giriş denemesini kaydet"""
    try:
        conn = get_db()
        conn.run('''
            INSERT INTO giris_denemeleri (telefon, ip_adresi, basarili) 
            VALUES (:p1, :p2, :p3)
        ''', p1=telefon, p2=ip_adresi, p3=basarili)
        conn.close()
    except:
        pass

def sifre_var_mi(telefon):
    """Kullanıcının şifresi var mı kontrol et"""
    try:
        conn = get_db()
        rows = conn.run('SELECT sifre_hash FROM kullanici_sifreler WHERE telefon = :p1', p1=telefon)
        conn.close()
        return rows[0][0] if rows else None
    except:
        return None

def sifre_kaydet(telefon, sifre):
    """Yeni şifre kaydet veya güncelle"""
    try:
        conn = get_db()
        sifre_hash = hash_sifre(sifre)
        try:
            conn.run('INSERT INTO kullanici_sifreler (telefon, sifre_hash) VALUES (:p1, :p2)', 
                    p1=telefon, p2=sifre_hash)
        except:
            conn.run('UPDATE kullanici_sifreler SET sifre_hash = :p1 WHERE telefon = :p2', 
                    p1=sifre_hash, p2=telefon)
        conn.close()
        return True
    except:
        return False

def yeni_captcha():
    """Yeni CAPTCHA sorusu oluştur"""
    sayi1 = random.randint(1, 10)
    sayi2 = random.randint(1, 10)
    session['captcha_cevap'] = sayi1 + sayi2
    return f"{sayi1} + {sayi2}"

@app.route('/')
def giris():
    if 'telefon' in session:
        return redirect(url_for('takvim'))
    # CAPTCHA oluştur
    sayi1 = random.randint(1, 10)
    sayi2 = random.randint(1, 10)
    session['captcha_cevap'] = sayi1 + sayi2
    return render_template('giris.html', captcha_soru=f"{sayi1} + {sayi2}")

@app.route('/login', methods=['POST'])
def login():
    telefon = request.form.get('telefon', '').strip()
    sifre = request.form.get('sifre', '').strip()
    captcha = request.form.get('captcha', '').strip()
    honeypot = request.form.get('website', '')  # Bot tuzağı - boş olmalı
    ip_adresi = request.remote_addr
    
    # Bot kontrolü - honeypot dolu ise bot
    if honeypot:
        return render_template('giris.html', hata='Geçersiz istek', captcha_soru=yeni_captcha())
    
    # CAPTCHA kontrolü
    try:
        if int(captcha) != session.get('captcha_cevap'):
            return render_template('giris.html', hata='Güvenlik sorusu yanlış', captcha_soru=yeni_captcha())
    except:
        return render_template('giris.html', hata='Güvenlik sorusunu cevaplayın', captcha_soru=yeni_captcha())
    
    # Telefon formatla
    telefon = telefon.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if telefon.startswith('+90'):
        telefon = telefon[3:]
    elif telefon.startswith('0'):
        telefon = telefon[1:]
    
    # Kullanıcı kayıtlı mı?
    if telefon not in KULLANICILAR:
        return render_template('giris.html', hata='Bu numara kayıtlı değil', captcha_soru=yeni_captcha())
    
    # Hesap kilitli mi?
    if kullanici_kilitli_mi(telefon):
        return render_template('giris.html', hata='Çok fazla başarısız deneme. 15 dakika bekleyin.', captcha_soru=yeni_captcha())
    
    # Şifre var mı kontrol et
    kayitli_sifre = sifre_var_mi(telefon)
    
    if not kayitli_sifre:
        # İlk giriş - şifre belirleme sayfasına yönlendir
        session['temp_telefon'] = telefon
        return redirect(url_for('sifre_belirle'))
    
    # Şifre kontrolü
    if not sifre:
        return render_template('giris.html', hata='Şifre gerekli', telefon=telefon, captcha_soru=yeni_captcha())
    
    if not sifre_dogrula(sifre, kayitli_sifre):
        giris_denemesi_kaydet(telefon, ip_adresi, False)
        return render_template('giris.html', hata='Şifre hatalı', telefon=telefon, captcha_soru=yeni_captcha())
    
    # Başarılı giriş
    giris_denemesi_kaydet(telefon, ip_adresi, True)
    session['telefon'] = telefon
    session['isim'] = KULLANICILAR[telefon]['isim']
    session['admin'] = KULLANICILAR[telefon]['admin']
    
    if request.form.get('hatirla'):
        session.permanent = True
    
    return redirect(url_for('takvim'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('giris'))

@app.route('/sifre-belirle')
def sifre_belirle():
    if 'temp_telefon' not in session:
        return redirect(url_for('giris'))
    telefon = session['temp_telefon']
    isim = KULLANICILAR.get(telefon, {}).get('isim', '')
    return render_template('sifre_belirle.html', isim=isim)

@app.route('/sifre-kaydet', methods=['POST'])
def sifre_kaydet_route():
    if 'temp_telefon' not in session:
        return redirect(url_for('giris'))
    
    telefon = session['temp_telefon']
    sifre = request.form.get('sifre', '').strip()
    sifre_tekrar = request.form.get('sifre_tekrar', '').strip()
    
    # Validasyon
    if len(sifre) < 6:
        return render_template('sifre_belirle.html', 
                             isim=KULLANICILAR[telefon]['isim'],
                             hata='Şifre en az 6 karakter olmalı')
    
    if sifre != sifre_tekrar:
        return render_template('sifre_belirle.html', 
                             isim=KULLANICILAR[telefon]['isim'],
                             hata='Şifreler eşleşmiyor')
    
    # Şifreyi kaydet
    if sifre_kaydet(telefon, sifre):
        session.pop('temp_telefon', None)
        session['telefon'] = telefon
        session['isim'] = KULLANICILAR[telefon]['isim']
        session['admin'] = KULLANICILAR[telefon]['admin']
        session.permanent = True
        return redirect(url_for('takvim'))
    else:
        return render_template('sifre_belirle.html', 
                             isim=KULLANICILAR[telefon]['isim'],
                             hata='Bir hata oluştu, tekrar deneyin')

@app.route('/api/admin/sifre-sifirla', methods=['POST'])
@login_required
def admin_sifre_sifirla():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetkiniz yok'})
    
    data = request.json
    telefon = data.get('telefon', '').strip()
    
    if telefon not in KULLANICILAR:
        return jsonify({'success': False, 'error': 'Kullanıcı bulunamadı'})
    
    try:
        conn = get_db()
        conn.run('DELETE FROM kullanici_sifreler WHERE telefon = :p1', p1=telefon)
        conn.close()
        return jsonify({'success': True, 'mesaj': f'{KULLANICILAR[telefon]["isim"]} şifresi sıfırlandı'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/sifre-durumu')
@login_required
def admin_sifre_durumu():
    if not session.get('admin'):
        return jsonify({'error': 'Yetkiniz yok'})
    
    try:
        conn = get_db()
        rows = conn.run('SELECT telefon FROM kullanici_sifreler')
        conn.close()
        return jsonify({'sifreli': [r[0] for r in rows]})
    except Exception as e:
        return jsonify({'sifreli': [], 'error': str(e)})

@app.route('/takvim')
@login_required
def takvim():
    return render_template('takvim.html', isim=session['isim'], admin=session['admin'])

@app.route('/pratik')
@login_required
def pratik():
    return render_template('pratik.html', isim=session['isim'], admin=session['admin'])

@app.route('/pratik-istatistik')
@login_required
def pratik_istatistik():
    return render_template('pratik_istatistik.html', isim=session['isim'], admin=session['admin'])

@app.route('/admin')
@login_required
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('takvim'))
    return render_template('admin.html', isim=session['isim'], admin=session['admin'], kullanicilar=KULLANICILAR)

# ==================== GÖREV TAKİP ====================

@app.route('/gorev-takip')
@login_required
def gorev_takip():
    telefon = session['telefon']
    if telefon not in GOREV_ERISIM:
        return redirect(url_for('takvim'))
    
    rol = GOREV_ERISIM[telefon]
    return render_template('gorev_takip.html', isim=session['isim'], rol=rol)

@app.route('/api/gorevler')
@login_required
def api_gorevler():
    telefon = session['telefon']
    if telefon not in GOREV_ERISIM:
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    try:
        conn = get_db()
        gorevler = conn.run('''
            SELECT id, baslik, durum, created_at, updated_at 
            FROM gorevler 
            ORDER BY 
                CASE durum 
                    WHEN 'bekliyor' THEN 1 
                    WHEN 'yapildi_iddia' THEN 2 
                    WHEN 'tamamlandi' THEN 3 
                END,
                created_at DESC
        ''')
        
        result = []
        for g in gorevler:
            notlar = conn.run('''
                SELECT yazar, yazar_isim, not_text, created_at 
                FROM gorev_notlar 
                WHERE gorev_id = :p1 
                ORDER BY created_at ASC
            ''', p1=g[0])
            
            result.append({
                'id': g[0],
                'baslik': g[1],
                'durum': g[2],
                'tarih': g[3].strftime('%Y-%m-%d') if g[3] else '',
                'notlar': [{
                    'yazar': n[0],
                    'yazar_isim': n[1],
                    'text': n[2],
                    'zaman': n[3].strftime('%H:%M') if n[3] else ''
                } for n in notlar]
            })
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gorev-ekle', methods=['POST'])
@login_required
def api_gorev_ekle():
    telefon = session['telefon']
    if telefon not in GOREV_ERISIM or GOREV_ERISIM[telefon] != 'admin':
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    data = request.json
    baslik = data.get('baslik', '').strip()
    
    if not baslik:
        return jsonify({'error': 'Görev başlığı gerekli'}), 400
    
    try:
        conn = get_db()
        conn.run('''
            INSERT INTO gorevler (baslik, olusturan) 
            VALUES (:p1, :p2)
        ''', p1=baslik, p2=session['telefon'])
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gorev-tick', methods=['POST'])
@login_required
def api_gorev_tick():
    telefon = session['telefon']
    if telefon not in GOREV_ERISIM:
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    data = request.json
    gorev_id = data.get('gorev_id')
    
    try:
        conn = get_db()
        conn.run('''
            UPDATE gorevler 
            SET durum = 'yapildi_iddia', updated_at = CURRENT_TIMESTAMP 
            WHERE id = :p1
        ''', p1=gorev_id)
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gorev-onayla', methods=['POST'])
@login_required
def api_gorev_onayla():
    telefon = session['telefon']
    if telefon not in GOREV_ERISIM or GOREV_ERISIM[telefon] != 'admin':
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    data = request.json
    gorev_id = data.get('gorev_id')
    
    try:
        conn = get_db()
        conn.run('''
            UPDATE gorevler 
            SET durum = 'tamamlandi', updated_at = CURRENT_TIMESTAMP 
            WHERE id = :p1
        ''', p1=gorev_id)
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gorev-reddet', methods=['POST'])
@login_required
def api_gorev_reddet():
    telefon = session['telefon']
    if telefon not in GOREV_ERISIM or GOREV_ERISIM[telefon] != 'admin':
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    data = request.json
    gorev_id = data.get('gorev_id')
    
    try:
        conn = get_db()
        conn.run('''
            UPDATE gorevler 
            SET durum = 'bekliyor', updated_at = CURRENT_TIMESTAMP 
            WHERE id = :p1
        ''', p1=gorev_id)
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gorev-not-ekle', methods=['POST'])
@login_required
def api_gorev_not_ekle():
    telefon = session['telefon']
    if telefon not in GOREV_ERISIM:
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    data = request.json
    gorev_id = data.get('gorev_id')
    not_text = data.get('not', '').strip()
    
    if not not_text:
        return jsonify({'error': 'Not boş olamaz'}), 400
    
    rol = GOREV_ERISIM[telefon]
    
    try:
        conn = get_db()
        conn.run('''
            INSERT INTO gorev_notlar (gorev_id, yazar, yazar_isim, not_text) 
            VALUES (:p1, :p2, :p3, :p4)
        ''', p1=gorev_id, p2=rol, p3=session['isim'], p4=not_text)
        
        conn.run('''
            UPDATE gorevler SET updated_at = CURRENT_TIMESTAMP WHERE id = :p1
        ''', p1=gorev_id)
        
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gorev-sil', methods=['POST'])
@login_required
def api_gorev_sil():
    telefon = session['telefon']
    if telefon not in GOREV_ERISIM or GOREV_ERISIM[telefon] != 'admin':
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    data = request.json
    gorev_id = data.get('gorev_id')
    
    try:
        conn = get_db()
        conn.run('DELETE FROM gorev_notlar WHERE gorev_id = :p1', p1=gorev_id)
        conn.run('DELETE FROM gorevler WHERE id = :p1', p1=gorev_id)
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== REZERVASYON API ====================

def saat_listesi_olustur(baslangic, bitis):
    saatler = []
    bas_saat, bas_dakika = map(int, baslangic.split(':'))
    bit_saat, bit_dakika = map(int, bitis.split(':'))
    
    current = bas_saat * 60 + bas_dakika
    end = bit_saat * 60 + bit_dakika
    
    while current < end:
        saat = f"{current // 60:02d}:{current % 60:02d}"
        saatler.append(saat)
        current += 30
    
    return saatler

def get_gun_saatleri(studyo, tarih):
    tarih_obj = datetime.strptime(tarih, '%Y-%m-%d') if isinstance(tarih, str) else tarih
    gun = tarih_obj.weekday()
    studyo_bilgi = STUDYOLAR[studyo]
    
    if gun < 5:  # Hafta içi
        saat_bilgi = studyo_bilgi['saatler']['hafta_ici']
    else:  # Hafta sonu
        saat_bilgi = studyo_bilgi['saatler']['hafta_sonu']
    
    return saat_listesi_olustur(saat_bilgi['baslangic'], saat_bilgi['bitis'])

@app.route('/api/studyolar')
@login_required
def api_studyolar():
    return jsonify(STUDYOLAR)

@app.route('/api/rezervasyonlar/<studyo>/<tarih>')
@login_required
def api_rezervasyonlar(studyo, tarih):
    try:
        conn = get_db()
        rows = conn.run('SELECT alan, saat, rezerve_eden, telefon, bloklu FROM rezervasyonlar WHERE studyo = :p1 AND tarih = :p2', p1=studyo, p2=tarih)
        conn.close()
        
        rezervasyonlar = {}
        for row in rows:
            alan = row[0]
            saat = row[1]
            if alan not in rezervasyonlar:
                rezervasyonlar[alan] = {}
            rezervasyonlar[alan][saat] = {
                'rezerve_eden': row[2],
                'telefon': row[3],
                'bloklu': row[4]
            }
        
        saatler = get_gun_saatleri(studyo, tarih)
        
        return jsonify({
            'rezervasyonlar': rezervasyonlar,
            'saatler': saatler,
            'alanlar': STUDYOLAR[studyo]['alanlar']
        })
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rezervasyon', methods=['POST'])
@login_required
def api_rezervasyon():
    try:
        data = request.json
        studyo = data['studyo']
        alan = data['alan']
        tarih = data['tarih']
        saat = data['saat']
        
        conn = get_db()
        
        # Önce mevcut durumu kontrol et
        rows = conn.run('SELECT rezerve_eden, bloklu FROM rezervasyonlar WHERE studyo = :p1 AND alan = :p2 AND tarih = :p3 AND saat = :p4', 
                       p1=studyo, p2=alan, p3=tarih, p4=saat)
        
        if rows:
            # Kayıt var
            mevcut = rows[0]
            if mevcut[1]:  # Bloklu
                conn.close()
                return jsonify({'success': False, 'error': 'Bu slot bloklanmış'})
            elif mevcut[0]:
                # Zaten rezerve edilmiş
                if mevcut[0] == session['isim']:
                    # Kendi rezervasyonunu iptal et
                    conn.run('DELETE FROM rezervasyonlar WHERE studyo = :p1 AND alan = :p2 AND tarih = :p3 AND saat = :p4', 
                            p1=studyo, p2=alan, p3=tarih, p4=saat)
                    conn.run('INSERT INTO aktiviteler (isim, islem, studyo, alan, tarih, saat) VALUES (:p1, :p2, :p3, :p4, :p5, :p6)',
                            p1=session['isim'], p2='iptal', p3=studyo, p4=alan, p5=tarih, p6=saat)
                    conn.close()
                    return jsonify({'success': True, 'mesaj': 'Rezervasyon iptal edildi'})
                else:
                    conn.close()
                    return jsonify({'success': False, 'error': f"Bu slot {mevcut[0]} tarafından rezerve edilmiş"})
        
        # Yeni rezervasyon yap
        try:
            conn.run('INSERT INTO rezervasyonlar (studyo, alan, tarih, saat, rezerve_eden, telefon) VALUES (:p1, :p2, :p3, :p4, :p5, :p6)',
                    p1=studyo, p2=alan, p3=tarih, p4=saat, p5=session['isim'], p6=session['telefon'])
        except:
            conn.run('UPDATE rezervasyonlar SET rezerve_eden = :p1, telefon = :p2 WHERE studyo = :p3 AND alan = :p4 AND tarih = :p5 AND saat = :p6',
                    p1=session['isim'], p2=session['telefon'], p3=studyo, p4=alan, p5=tarih, p6=saat)
        
        conn.run('INSERT INTO aktiviteler (isim, islem, studyo, alan, tarih, saat) VALUES (:p1, :p2, :p3, :p4, :p5, :p6)',
                p1=session['isim'], p2='rezervasyon', p3=studyo, p4=alan, p5=tarih, p6=saat)
        conn.close()
        
        return jsonify({'success': True, 'mesaj': 'Rezervasyon yapıldı'})
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/aktiviteler')
@login_required
def api_aktiviteler():
    try:
        conn = get_db()
        rows = conn.run('SELECT isim, islem, studyo, alan, tarih, saat, created_at FROM aktiviteler ORDER BY created_at DESC LIMIT 20')
        conn.close()
        
        aktiviteler = []
        for row in rows:
            created_at = row[6]
            now = datetime.now()
            diff = now - created_at
            
            if diff.total_seconds() < 60:
                zaman = 'Az önce'
            elif diff.total_seconds() < 3600:
                zaman = f'{int(diff.total_seconds() // 60)} dakika önce'
            elif diff.total_seconds() < 86400:
                zaman = f'{int(diff.total_seconds() // 3600)} saat önce'
            else:
                zaman = f'{diff.days} gün önce'
            
            tarih_str = row[4].strftime('%Y-%m-%d') if hasattr(row[4], 'strftime') else str(row[4])
            aktiviteler.append({'isim': row[0], 'islem': row[1], 'studyo': row[2], 'alan': row[3], 'tarih': tarih_str, 'saat': row[5], 'zaman': zaman})
        
        return jsonify(aktiviteler)
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify([])

@app.route('/api/admin/toplu-blok', methods=['POST'])
@login_required
def toplu_blok():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetkiniz yok'})
    try:
        data = request.json
        studyo = data['studyo']
        alan = data['alan']
        gunler = data['gunler']
        saat_bas = data['saat_baslangic']
        saat_bit = data['saat_bitis']
        islem_tipi = data['islem']
        
        gun_map = {'Pzt': 0, 'Sal': 1, 'Çar': 2, 'Car': 2, 'Per': 3, 'Cum': 4, 'Cmt': 5, 'Paz': 6}
        
        if 'hepsi' in gunler or 'Hepsi' in gunler:
            secili_gunler = [0, 1, 2, 3, 4, 5, 6]
        else:
            secili_gunler = [gun_map[g] for g in gunler if g in gun_map]
        
        saatler = saat_listesi_olustur(saat_bas, saat_bit)
        
        conn = get_db()
        bugun = datetime.now().date()
        islem_sayisi = 0
        
        for i in range(90):
            tarih = bugun + timedelta(days=i)
            if tarih.weekday() in secili_gunler:
                for saat in saatler:
                    tarih_str = tarih.strftime('%Y-%m-%d')
                    if islem_tipi == 'blokla':
                        try:
                            conn.run('INSERT INTO rezervasyonlar (studyo, alan, tarih, saat, bloklu) VALUES (:p1, :p2, :p3, :p4, TRUE)', p1=studyo, p2=alan, p3=tarih_str, p4=saat)
                        except:
                            conn.run('UPDATE rezervasyonlar SET bloklu = TRUE, rezerve_eden = NULL, telefon = NULL WHERE studyo = :p1 AND alan = :p2 AND tarih = :p3 AND saat = :p4', p1=studyo, p2=alan, p3=tarih_str, p4=saat)
                    else:
                        conn.run('DELETE FROM rezervasyonlar WHERE studyo = :p1 AND alan = :p2 AND tarih = :p3 AND saat = :p4 AND bloklu = TRUE', p1=studyo, p2=alan, p3=tarih_str, p4=saat)
                    islem_sayisi += 1
        
        conn.close()
        return jsonify({'success': True, 'mesaj': f'{islem_sayisi} slot güncellendi'})
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== PRATİK ANKETİ ====================

def anket_aktif_mi(lokasyon):
    """Pratik anketi aktif mi kontrol et"""
    pratik_gun = PRATIK_BILGI[lokasyon]['gun']
    bugun = datetime.now().date()
    bugun_gun = bugun.weekday()
    
    # Bu haftaki pratik gününü bul
    gun_farki = pratik_gun - bugun_gun
    if gun_farki < 0:
        gun_farki += 7
    
    pratik_tarihi = bugun + timedelta(days=gun_farki)
    
    # Anket pratik gününden 5 gün önce açılır, pratik saatinde kapanır
    anket_baslangic = pratik_tarihi - timedelta(days=5)
    
    return bugun >= anket_baslangic and bugun <= pratik_tarihi, pratik_tarihi

def pratik_mesaji_olustur(lokasyon, evet_listesi):
    """WhatsApp için pratik mesajı oluştur"""
    aktif, pratik_tarihi = anket_aktif_mi(lokasyon)
    
    gun_isimleri = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    ay_isimleri = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 
                  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
    
    tarih_str = f"{pratik_tarihi.day} {ay_isimleri[pratik_tarihi.month - 1]} {gun_isimleri[pratik_tarihi.weekday()]}"
    
    bilgi = PRATIK_BILGI[lokasyon]
    
    gorevli_listesi = list(evet_listesi)
    if lokasyon == 'sisli':
        gorevli_listesi = ['Uğur Altun'] + gorevli_listesi
    
    if gorevli_listesi:
        gorevliler = ", ".join(gorevli_listesi)
        mesaj = f"📅 {tarih_str}\n📍 {bilgi['yer']}\n⏰ {bilgi['saat']}\n\n👥 Pratik görevlileri: {gorevliler}."
    else:
        mesaj = f"📅 {tarih_str}\n📍 {bilgi['yer']}\n⏰ {bilgi['saat']}\n\n⚠️ Henüz görevli yok."
    
    return mesaj

@app.route('/api/pratik/durum')
@login_required
def pratik_durum():
    """Her iki lokasyon için anket durumu"""
    try:
        sonuc = {}
        conn = get_db()
        
        for lokasyon in ['sisli', 'kadikoy']:
            aktif, pratik_tarihi = anket_aktif_mi(lokasyon)
            tarih_str = pratik_tarihi.strftime('%Y-%m-%d')
            
            # Kullanıcının cevabı
            rows = conn.run('SELECT cevap FROM pratik_anket WHERE pratik_tarih = :p1 AND lokasyon = :p2 AND telefon = :p3', 
                          p1=tarih_str, p2=lokasyon, p3=session['telefon'])
            kullanici_cevap = rows[0][0] if rows else None
            
            # Tüm cevaplar
            evet_rows = conn.run('SELECT isim FROM pratik_anket WHERE pratik_tarih = :p1 AND lokasyon = :p2 AND cevap = :p3 ORDER BY created_at', 
                               p1=tarih_str, p2=lokasyon, p3='evet')
            hayir_rows = conn.run('SELECT isim FROM pratik_anket WHERE pratik_tarih = :p1 AND lokasyon = :p2 AND cevap = :p3 ORDER BY created_at', 
                                p1=tarih_str, p2=lokasyon, p3='hayir')
            
            evet_listesi = [r[0] for r in evet_rows]
            hayir_listesi = [r[0] for r in hayir_rows]
            
            if lokasyon == 'sisli':
                evet_listesi = [x for x in evet_listesi if x != 'Uğur Altun']
                hayir_listesi = [x for x in hayir_listesi if x != 'Uğur Altun']
            
            mesaj = pratik_mesaji_olustur(lokasyon, evet_listesi)
            
            gun_isimleri = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
            ay_isimleri = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 
                          'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
            
            sonuc[lokasyon] = {
                'aktif': aktif,
                'pratik_tarih': tarih_str,
                'pratik_tarih_str': f"{pratik_tarihi.day} {ay_isimleri[pratik_tarihi.month - 1]} {gun_isimleri[pratik_tarihi.weekday()]}",
                'saat': PRATIK_BILGI[lokasyon]['saat'],
                'yer': PRATIK_BILGI[lokasyon]['yer'],
                'kullanici_cevap': kullanici_cevap,
                'evet_listesi': evet_listesi,
                'hayir_listesi': hayir_listesi,
                'mesaj': mesaj
            }
        
        conn.close()
        return jsonify(sonuc)
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/pratik/oyla', methods=['POST'])
@login_required
def pratik_oyla():
    """Pratik anketi oylama"""
    try:
        data = request.json
        lokasyon = data['lokasyon']
        cevap = data['cevap']  # 'evet' veya 'hayir'
        
        aktif, pratik_tarihi = anket_aktif_mi(lokasyon)
        if not aktif:
            return jsonify({'success': False, 'error': 'Anket şu anda kapalı'})
        
        tarih_str = pratik_tarihi.strftime('%Y-%m-%d')
        
        conn = get_db()
        
        # Önceki cevabı sil
        conn.run('DELETE FROM pratik_anket WHERE pratik_tarih = :p1 AND lokasyon = :p2 AND telefon = :p3',
                p1=tarih_str, p2=lokasyon, p3=session['telefon'])
        
        # Yeni cevap ekle
        conn.run('INSERT INTO pratik_anket (pratik_tarih, lokasyon, telefon, isim, cevap) VALUES (:p1, :p2, :p3, :p4, :p5)',
                p1=tarih_str, p2=lokasyon, p3=session['telefon'], p4=session['isim'], p5=cevap)
        
        # Eğer evet ise görevli tablosuna da ekle
        if cevap == 'evet':
            try:
                conn.run('INSERT INTO pratik_gorevli (pratik_tarih, lokasyon, telefon, isim) VALUES (:p1, :p2, :p3, :p4)',
                        p1=tarih_str, p2=lokasyon, p3=session['telefon'], p4=session['isim'])
            except:
                pass  # Zaten var
        else:
            conn.run('DELETE FROM pratik_gorevli WHERE pratik_tarih = :p1 AND lokasyon = :p2 AND telefon = :p3',
                    p1=tarih_str, p2=lokasyon, p3=session['telefon'])
        
        conn.close()
        
        return jsonify({'success': True, 'mesaj': 'Oyunuz kaydedildi!'})
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pratik/istatistik')
@login_required
def pratik_istatistik_api():
    """Pratik görevli istatistikleri"""
    try:
        conn = get_db()
        
        # Şişli istatistikleri
        sisli_rows = conn.run('''
            SELECT isim, COUNT(*) as sayi 
            FROM pratik_gorevli 
            WHERE lokasyon = :p1 
            GROUP BY isim 
            ORDER BY sayi DESC, isim
        ''', p1='sisli')
        
        # Kadıköy istatistikleri
        kadikoy_rows = conn.run('''
            SELECT isim, COUNT(*) as sayi 
            FROM pratik_gorevli 
            WHERE lokasyon = :p1 
            GROUP BY isim 
            ORDER BY sayi DESC, isim
        ''', p1='kadikoy')
        
        # Toplam istatistikler
        toplam_rows = conn.run('''
            SELECT isim, COUNT(*) as sayi 
            FROM pratik_gorevli 
            GROUP BY isim 
            ORDER BY sayi DESC, isim
        ''')
        
        # Son pratikler
        son_pratikler = conn.run('''
            SELECT pratik_tarih, lokasyon, isim 
            FROM pratik_gorevli 
            ORDER BY pratik_tarih DESC, lokasyon, isim
            LIMIT 50
        ''')
        
        conn.close()
        
        return jsonify({
            'sisli': [{'isim': r[0], 'sayi': r[1]} for r in sisli_rows],
            'kadikoy': [{'isim': r[0], 'sayi': r[1]} for r in kadikoy_rows],
            'toplam': [{'isim': r[0], 'sayi': r[1]} for r in toplam_rows],
            'son_pratikler': [{'tarih': str(r[0]), 'lokasyon': r[1], 'isim': r[2]} for r in son_pratikler]
        })
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
