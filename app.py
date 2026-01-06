from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'swingplanet-gizli-anahtar-2026'

# ==================== KULLANICI LİSTESİ ====================
# Buraya ekip arkadaşlarının numaralarını ekle
KULLANICILAR = {
    # Admin'ler
    "5550001111": {"isim": "Ugur", "admin": True},
    "5550002222": {"isim": "Bilge", "admin": True},
    
    # Ekip
    "5409171998": {"isim": "Kübra Gözde", "admin": False},
    "5347666377": {"isim": "Berfin", "admin": False},
    "5074942445": {"isim": "Özhan", "admin": False},
    "5367194693": {"isim": "Mert", "admin": False},
    "5417383748": {"isim": "Duygu", "admin": False},
    "5364906694": {"isim": "Ceyhan", "admin": False},
    "5425614963": {"isim": "Büşra", "admin": False},
    "5307013845": {"isim": "Tuğçe", "admin": False},
    "5434564332": {"isim": "Enes", "admin": False},
    "5377974644": {"isim": "Serpil", "admin": False},
    "5357132619": {"isim": "Alperen", "admin": False},
    "5448482424": {"isim": "Zehra", "admin": False},
    "5348878568": {"isim": "Muhammet", "admin": False},
    "5350279213": {"isim": "Emre", "admin": False},
    "5335437664": {"isim": "İlker", "admin": False},
    "5302821881": {"isim": "Kayhan", "admin": False},
    "5367777965": {"isim": "Başak", "admin": False},
    "5455151266": {"isim": "Atacan", "admin": False},
    "5352041658": {"isim": "Mustafa", "admin": False},
}

# ==================== STÜDYO AYARLARI ====================
STUDYOLAR = {
    "kadikoy": {
        "isim": "Kadıköy",
        "alanlar": ["Ana Salon"],
        "hafta_ici_baslangic": 16,  # 16:00
        "haftasonu_baslangic": 12,  # 12:00
        "bitis": 22,  # 22:00
    },
    "sisli": {
        "isim": "Şişli",
        "alanlar": ["Büyük Stüdyo", "Küçük Stüdyo", "Perdeli Alan"],
        "hafta_ici_baslangic": 12,
        "haftasonu_baslangic": 12,
        "bitis": 22,
    }
}

# ==================== VERİTABANI ====================
def get_db():
    db = sqlite3.connect('rezervasyonlar.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS rezervasyonlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            studyo TEXT NOT NULL,
            alan TEXT NOT NULL,
            tarih TEXT NOT NULL,
            saat TEXT NOT NULL,
            rezerve_eden TEXT,
            telefon TEXT,
            bloklu INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(studyo, alan, tarih, saat)
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS aktiviteler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT NOT NULL,
            islem TEXT NOT NULL,
            studyo TEXT NOT NULL,
            alan TEXT NOT NULL,
            tarih TEXT NOT NULL,
            saat TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    db.close()

init_db()

# ==================== YARDIMCI FONKSİYONLAR ====================
def saat_slotlari_olustur(baslangic, bitis):
    """30 dakikalık slotlar oluşturur"""
    slotlar = []
    saat = baslangic
    dakika = 0
    while saat < bitis:
        slotlar.append(f"{saat:02d}:{dakika:02d}")
        dakika += 30
        if dakika >= 60:
            dakika = 0
            saat += 1
    return slotlar

def gun_slotlari_getir(studyo_key, tarih_str):
    """Belirli bir gün için uygun slotları getirir"""
    studyo = STUDYOLAR[studyo_key]
    tarih = datetime.strptime(tarih_str, "%Y-%m-%d")
    gun = tarih.weekday()  # 0=Pazartesi, 6=Pazar
    
    if gun < 5:  # Hafta içi
        baslangic = studyo["hafta_ici_baslangic"]
    else:  # Haftasonu
        baslangic = studyo["haftasonu_baslangic"]
    
    return saat_slotlari_olustur(baslangic, studyo["bitis"])

def rezervasyon_getir(studyo, alan, tarih, saat):
    db = get_db()
    rez = db.execute(
        'SELECT * FROM rezervasyonlar WHERE studyo=? AND alan=? AND tarih=? AND saat=?',
        (studyo, alan, tarih, saat)
    ).fetchone()
    db.close()
    return rez

# ==================== ROTALAR ====================
@app.route('/')
def giris():
    if 'telefon' in session:
        return redirect('/takvim')
    return render_template('giris.html')

@app.route('/login', methods=['POST'])
def login():
    telefon = request.form.get('telefon', '').replace(' ', '').replace('-', '')
    # Başında 0 varsa kaldır
    if telefon.startswith('0'):
        telefon = telefon[1:]
    
    if telefon in KULLANICILAR:
        session['telefon'] = telefon
        session['isim'] = KULLANICILAR[telefon]['isim']
        session['admin'] = KULLANICILAR[telefon]['admin']
        return redirect('/takvim')
    else:
        return render_template('giris.html', hata="Bu numara kayıtlı değil!")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/takvim')
def takvim():
    if 'telefon' not in session:
        return redirect('/')
    
    # Bugünden başlayarak 14 gün göster
    bugun = datetime.now()
    gunler = []
    for i in range(14):
        gun = bugun + timedelta(days=i)
        gunler.append({
            'tarih': gun.strftime('%Y-%m-%d'),
            'gun_adi': ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'][gun.weekday()],
            'gun_no': gun.day,
            'ay': ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'][gun.month - 1]
        })
    
    return render_template('takvim.html', 
                         gunler=gunler,
                         studyolar=STUDYOLAR,
                         isim=session['isim'],
                         admin=session['admin'])

@app.route('/api/slotlar/<studyo>/<alan>/<tarih>')
def slotlar_getir(studyo, alan, tarih):
    if 'telefon' not in session:
        return jsonify({'error': 'Yetkisiz'}), 401
    
    slotlar = gun_slotlari_getir(studyo, tarih)
    
    db = get_db()
    rezervasyonlar = db.execute(
        'SELECT * FROM rezervasyonlar WHERE studyo=? AND alan=? AND tarih=?',
        (studyo, alan, tarih)
    ).fetchall()
    db.close()
    
    rez_dict = {r['saat']: dict(r) for r in rezervasyonlar}
    
    sonuc = []
    for slot in slotlar:
        if slot in rez_dict:
            r = rez_dict[slot]
            sonuc.append({
                'saat': slot,
                'durum': 'bloklu' if r['bloklu'] else 'dolu',
                'kisi': r['rezerve_eden'] if not r['bloklu'] else None,
                'kendi_mi': r['telefon'] == session['telefon']
            })
        else:
            sonuc.append({
                'saat': slot,
                'durum': 'bos',
                'kisi': None,
                'kendi_mi': False
            })
    
    return jsonify(sonuc)

@app.route('/api/rezerve', methods=['POST'])
def rezerve_et():
    if 'telefon' not in session:
        return jsonify({'error': 'Yetkisiz'}), 401
    
    data = request.json
    studyo = data['studyo']
    alan = data['alan']
    tarih = data['tarih']
    saat = data['saat']
    
    # Zaten rezerve mi kontrol et
    mevcut = rezervasyon_getir(studyo, alan, tarih, saat)
    if mevcut:
        return jsonify({'error': 'Bu slot zaten dolu!'}), 400
    
    db = get_db()
    db.execute(
        'INSERT INTO rezervasyonlar (studyo, alan, tarih, saat, rezerve_eden, telefon, bloklu) VALUES (?, ?, ?, ?, ?, ?, 0)',
        (studyo, alan, tarih, saat, session['isim'], session['telefon'])
    )
    # Aktivite kaydet
    db.execute(
        'INSERT INTO aktiviteler (isim, islem, studyo, alan, tarih, saat) VALUES (?, ?, ?, ?, ?, ?)',
        (session['isim'], 'rezerve', studyo, alan, tarih, saat)
    )
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'mesaj': f'{saat} rezerve edildi!'})

@app.route('/api/iptal', methods=['POST'])
def iptal_et():
    if 'telefon' not in session:
        return jsonify({'error': 'Yetkisiz'}), 401
    
    data = request.json
    studyo = data['studyo']
    alan = data['alan']
    tarih = data['tarih']
    saat = data['saat']
    
    mevcut = rezervasyon_getir(studyo, alan, tarih, saat)
    if not mevcut:
        return jsonify({'error': 'Rezervasyon bulunamadı'}), 400
    
    # Sadece kendi rezervasyonunu veya admin ise iptal edebilir
    if mevcut['telefon'] != session['telefon'] and not session['admin']:
        return jsonify({'error': 'Bu rezervasyonu iptal edemezsiniz'}), 403
    
    db = get_db()
    db.execute(
        'DELETE FROM rezervasyonlar WHERE studyo=? AND alan=? AND tarih=? AND saat=?',
        (studyo, alan, tarih, saat)
    )
    # Aktivite kaydet
    db.execute(
        'INSERT INTO aktiviteler (isim, islem, studyo, alan, tarih, saat) VALUES (?, ?, ?, ?, ?, ?)',
        (session['isim'], 'iptal', studyo, alan, tarih, saat)
    )
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'mesaj': 'Rezervasyon iptal edildi'})

# ==================== ADMİN İŞLEMLERİ ====================

@app.route('/api/aktiviteler')
def aktiviteler_getir():
    if 'telefon' not in session:
        return jsonify({'error': 'Yetkisiz'}), 401
    
    db = get_db()
    aktiviteler = db.execute(
        'SELECT * FROM aktiviteler ORDER BY created_at DESC LIMIT 30'
    ).fetchall()
    db.close()
    
    sonuc = []
    for a in aktiviteler:
        # Zaman farkını hesapla
        created = datetime.strptime(a['created_at'], '%Y-%m-%d %H:%M:%S')
        simdi = datetime.now()
        fark = simdi - created
        
        if fark.total_seconds() < 60:
            zaman = "Az önce"
        elif fark.total_seconds() < 3600:
            zaman = f"{int(fark.total_seconds() // 60)} dk önce"
        elif fark.total_seconds() < 86400:
            zaman = f"{int(fark.total_seconds() // 3600)} saat önce"
        else:
            zaman = f"{int(fark.days)} gün önce"
        
        sonuc.append({
            'isim': a['isim'],
            'islem': a['islem'],
            'studyo': STUDYOLAR[a['studyo']]['isim'],
            'alan': a['alan'],
            'tarih': a['tarih'],
            'saat': a['saat'],
            'zaman': zaman
        })
    
    return jsonify(sonuc)

@app.route('/api/admin/toplu-blok', methods=['POST'])
def toplu_blok():
    if 'telefon' not in session or not session['admin']:
        return jsonify({'error': 'Yetkisiz'}), 403
    
    data = request.json
    studyo = data['studyo']
    alan = data['alan']
    gunler = data['gunler']  # ['Pzt', 'Sal', ...] veya ['hepsi']
    saat_baslangic = data['saat_baslangic']  # "12:00"
    saat_bitis = data['saat_bitis']  # "17:00"
    islem = data['islem']  # 'blokla' veya 'ac'
    
    gun_map = {'Pzt': 0, 'Sal': 1, 'Çar': 2, 'Per': 3, 'Cum': 4, 'Cmt': 5, 'Paz': 6}
    
    # Gelecek 14 gün için işlem yap
    bugun = datetime.now()
    db = get_db()
    islem_sayisi = 0
    
    for i in range(14):
        gun = bugun + timedelta(days=i)
        gun_adi = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'][gun.weekday()]
        
        if 'hepsi' not in gunler and gun_adi not in gunler:
            continue
        
        tarih_str = gun.strftime('%Y-%m-%d')
        slotlar = gun_slotlari_getir(studyo, tarih_str)
        
        for slot in slotlar:
            if slot >= saat_baslangic and slot < saat_bitis:
                if islem == 'blokla':
                    try:
                        db.execute(
                            'INSERT OR REPLACE INTO rezervasyonlar (studyo, alan, tarih, saat, bloklu) VALUES (?, ?, ?, ?, 1)',
                            (studyo, alan, tarih_str, slot)
                        )
                        islem_sayisi += 1
                    except:
                        pass
                else:  # aç
                    db.execute(
                        'DELETE FROM rezervasyonlar WHERE studyo=? AND alan=? AND tarih=? AND saat=? AND bloklu=1',
                        (studyo, alan, tarih_str, slot)
                    )
                    islem_sayisi += 1
    
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'mesaj': f'{islem_sayisi} slot {"bloklandı" if islem == "blokla" else "açıldı"}'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
