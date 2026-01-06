from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import pg8000.native
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'swing-planet-2024-secret-key'
app.config['JSON_AS_ASCII'] = False  # Türkçe karakterler için

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
    conn.close()

try:
    init_db()
except:
    pass

KULLANICILAR = {
    # Admin'ler
    "5550001111": {"isim": "Uğur Altun", "admin": True},
    "5550002222": {"isim": "Bilge Kocabaş", "admin": True},
    
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

def saat_listesi_olustur(baslangic, bitis):
    saatler = []
    bas_saat, bas_dk = map(int, baslangic.split(':'))
    bit_saat, bit_dk = map(int, bitis.split(':'))
    current = bas_saat * 60 + bas_dk
    end = bit_saat * 60 + bit_dk
    while current < end:
        saat = f"{current // 60:02d}:{current % 60:02d}"
        saatler.append(saat)
        current += 30
    return saatler

def get_pratik_tarihi(lokasyon):
    """Bu haftanın pratik tarihini bul"""
    bugun = datetime.now().date()
    hedef_gun = PRATIK_BILGI[lokasyon]['gun']
    
    # Bu haftanın pazartesisi
    pazartesi = bugun - timedelta(days=bugun.weekday())
    
    # Bu haftanın pratik günü
    pratik_tarihi = pazartesi + timedelta(days=hedef_gun)
    
    return pratik_tarihi

def anket_aktif_mi(lokasyon):
    """Anket aktif mi kontrol et"""
    now = datetime.now()
    bugun = now.date()
    
    # Bu haftanın pazartesisi
    pazartesi = bugun - timedelta(days=bugun.weekday())
    
    pratik_tarihi = get_pratik_tarihi(lokasyon)
    
    # Pazartesi 00:00'dan pratik günü 23:59'a kadar açık
    if pazartesi <= bugun <= pratik_tarihi:
        return True, pratik_tarihi
    
    return False, pratik_tarihi

def pratik_mesaji_olustur(lokasyon, gorevliler):
    """WhatsApp mesajı oluştur"""
    pratik_tarihi = get_pratik_tarihi(lokasyon)
    bilgi = PRATIK_BILGI[lokasyon]
    
    gun_isimleri = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    ay_isimleri = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 
                   'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
    
    gun_adi = gun_isimleri[pratik_tarihi.weekday()]
    tarih_str = f"{pratik_tarihi.day} {ay_isimleri[pratik_tarihi.month - 1]}"
    
    gorevli_listesi = list(gorevliler)
    
    # Şişli için özel durum (gizli)
    if lokasyon == 'sisli':
        ozel_isim = 'Uğur Altun'
        if ozel_isim not in gorevli_listesi:
            gorevli_listesi = [ozel_isim] + gorevli_listesi
        elif gorevli_listesi[0] != ozel_isim:
            gorevli_listesi.remove(ozel_isim)
            gorevli_listesi = [ozel_isim] + gorevli_listesi
    
    gorevli_str = ', '.join(gorevli_listesi) if gorevli_listesi else 'Henüz belli değil'
    
    mesaj = f"""Bugün, {tarih_str} {gun_adi}, saat {bilgi['saat']} saatleri arası {bilgi['yer']}'de pratik yapabilirsiniz.

Pratik görevlileri: {gorevli_str}.

Sevgiler ✨"""
    
    return mesaj

@app.route('/')
def giris():
    if 'telefon' in session:
        return redirect(url_for('takvim'))
    return render_template('giris.html')

@app.route('/login', methods=['POST'])
def login():
    telefon = request.form.get('telefon', '').strip()
    telefon = telefon.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if telefon.startswith('+90'):
        telefon = telefon[3:]
    elif telefon.startswith('0'):
        telefon = telefon[1:]
    if telefon in KULLANICILAR:
        session['telefon'] = telefon
        session['isim'] = KULLANICILAR[telefon]['isim']
        session['admin'] = KULLANICILAR[telefon]['admin']
        return redirect(url_for('takvim'))
    else:
        return render_template('giris.html', hata='Bu numara kayıtlı değil')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('giris'))

@app.route('/takvim')
@login_required
def takvim():
    return render_template('takvim.html', isim=session['isim'], admin=session['admin'], studyolar=STUDYOLAR)

@app.route('/pratik')
@login_required
def pratik():
    return render_template('pratik.html', isim=session['isim'], admin=session['admin'])

@app.route('/pratik-istatistik')
@login_required
def pratik_istatistik():
    return render_template('pratik_istatistik.html', isim=session['isim'], admin=session['admin'])

@app.route('/api/slotlar/<studyo>/<alan>/<tarih>')
@login_required
def get_slotlar(studyo, alan, tarih):
    try:
        tarih_obj = datetime.strptime(tarih, '%Y-%m-%d')
        gun = tarih_obj.weekday()
        studyo_bilgi = STUDYOLAR.get(studyo)
        if not studyo_bilgi:
            return jsonify([])
        if gun < 5:
            saat_bilgi = studyo_bilgi['saatler']['hafta_ici']
        else:
            saat_bilgi = studyo_bilgi['saatler']['hafta_sonu']
        saatler = saat_listesi_olustur(saat_bilgi['baslangic'], saat_bilgi['bitis'])
        
        conn = get_db()
        rows = conn.run('SELECT saat, rezerve_eden, telefon, bloklu FROM rezervasyonlar WHERE studyo = :p1 AND alan = :p2 AND tarih = :p3', p1=studyo, p2=alan, p3=tarih)
        conn.close()
        
        rezervasyonlar = {}
        for row in rows:
            rezervasyonlar[row[0]] = {'saat': row[0], 'rezerve_eden': row[1], 'telefon': row[2], 'bloklu': row[3]}
        
        slotlar = []
        for saat in saatler:
            rez = rezervasyonlar.get(saat)
            if rez:
                if rez['bloklu']:
                    durum = 'bloklu'
                    kisi = None
                    kendi_mi = False
                else:
                    durum = 'dolu'
                    kisi = rez['rezerve_eden']
                    kendi_mi = (rez['telefon'] == session['telefon'])
            else:
                durum = 'bos'
                kisi = None
                kendi_mi = False
            slotlar.append({'saat': saat, 'durum': durum, 'kisi': kisi, 'kendi_mi': kendi_mi})
        return jsonify(slotlar)
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify([])

@app.route('/api/rezerve', methods=['POST'])
@login_required
def rezerve():
    try:
        data = request.json
        studyo = data['studyo']
        alan = data['alan']
        tarih = data['tarih']
        saat = data['saat']
        
        conn = get_db()
        rows = conn.run('SELECT id FROM rezervasyonlar WHERE studyo = :p1 AND alan = :p2 AND tarih = :p3 AND saat = :p4', p1=studyo, p2=alan, p3=tarih, p4=saat)
        
        if rows:
            conn.close()
            return jsonify({'success': False, 'error': 'Bu slot zaten dolu'})
        
        conn.run('INSERT INTO rezervasyonlar (studyo, alan, tarih, saat, rezerve_eden, telefon) VALUES (:p1, :p2, :p3, :p4, :p5, :p6)', p1=studyo, p2=alan, p3=tarih, p4=saat, p5=session['isim'], p6=session['telefon'])
        
        studyo_isim = STUDYOLAR[studyo]['isim']
        conn.run('INSERT INTO aktiviteler (isim, islem, studyo, alan, tarih, saat) VALUES (:p1, :p2, :p3, :p4, :p5, :p6)', p1=session['isim'], p2='rezerve', p3=studyo_isim, p4=alan, p5=tarih, p6=saat)
        conn.close()
        
        return jsonify({'success': True, 'mesaj': 'Rezervasyon yapıldı!'})
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/iptal', methods=['POST'])
@login_required
def iptal():
    try:
        data = request.json
        studyo = data['studyo']
        alan = data['alan']
        tarih = data['tarih']
        saat = data['saat']
        
        conn = get_db()
        rows = conn.run('SELECT rezerve_eden, telefon FROM rezervasyonlar WHERE studyo = :p1 AND alan = :p2 AND tarih = :p3 AND saat = :p4', p1=studyo, p2=alan, p3=tarih, p4=saat)
        
        if not rows:
            conn.close()
            return jsonify({'success': False, 'error': 'Rezervasyon bulunamadı'})
        
        telefon = rows[0][1]
        if telefon != session['telefon'] and not session.get('admin'):
            conn.close()
            return jsonify({'success': False, 'error': 'Bu rezervasyonu iptal edemezsiniz'})
        
        conn.run('DELETE FROM rezervasyonlar WHERE studyo = :p1 AND alan = :p2 AND tarih = :p3 AND saat = :p4', p1=studyo, p2=alan, p3=tarih, p4=saat)
        
        studyo_isim = STUDYOLAR[studyo]['isim']
        conn.run('INSERT INTO aktiviteler (isim, islem, studyo, alan, tarih, saat) VALUES (:p1, :p2, :p3, :p4, :p5, :p6)', p1=session['isim'], p2='iptal', p3=studyo_isim, p4=alan, p5=tarih, p6=saat)
        conn.close()
        
        return jsonify({'success': True, 'mesaj': 'Rezervasyon iptal edildi'})
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/aktiviteler')
@login_required
def get_aktiviteler():
    try:
        conn = get_db()
        rows = conn.run('SELECT isim, islem, studyo, alan, tarih, saat, created_at FROM aktiviteler ORDER BY created_at DESC LIMIT 30')
        conn.close()
        
        aktiviteler = []
        for row in rows:
            created = row[6]
            now = datetime.now()
            if isinstance(created, datetime):
                diff = now - created
            else:
                diff = timedelta(seconds=0)
            
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

# ==================== PRATİK ANKETİ API ====================

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
            
            # Mesaj oluştur
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
