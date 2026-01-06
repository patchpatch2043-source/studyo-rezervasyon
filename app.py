from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'swing-planet-2024-secret-key'

DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
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
    cur.execute('''
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
    conn.commit()
    cur.close()
    conn.close()

with app.app_context():
    init_db()

KULLANICILAR = {
    "5550001111": {"isim": "Ugur", "admin": True},
    "5550002222": {"isim": "Bilge", "admin": True},
    "5409171998": {"isim": "Kubra Gozde", "admin": False},
    "5347666377": {"isim": "Berfin", "admin": False},
    "5074942445": {"isim": "Ozhan", "admin": False},
    "5367194693": {"isim": "Mert", "admin": False},
    "5417383748": {"isim": "Duygu", "admin": False},
    "5364906694": {"isim": "Ceyhan", "admin": False},
    "5425614963": {"isim": "Busra", "admin": False},
    "5307013845": {"isim": "Tugce", "admin": False},
    "5434564332": {"isim": "Enes", "admin": False},
    "5377974644": {"isim": "Serpil", "admin": False},
    "5357132619": {"isim": "Alperen", "admin": False},
    "5448482424": {"isim": "Zehra Ergul", "admin": False},
    "5348878568": {"isim": "Muhammet", "admin": False},
    "5350279213": {"isim": "Emre Agdas", "admin": False},
    "5335437664": {"isim": "Ilker", "admin": False},
    "5302821881": {"isim": "Kayhan", "admin": False},
    "5367777965": {"isim": "Basak", "admin": False},
    "5455151266": {"isim": "Atacan", "admin": False},
    "5528451111": {"isim": "Emre Gokalp", "admin": False},
    "5064568591": {"isim": "Funda", "admin": False},
    "5383537044": {"isim": "Nida", "admin": False},
    "5075277754": {"isim": "Zehra Erek", "admin": False},
    "5050230175": {"isim": "Beyza", "admin": False},
    "5066735330": {"isim": "Ozge", "admin": False},
    "5068647964": {"isim": "Ceyda", "admin": False},
}

STUDYOLAR = {
    'kadikoy': {
        'isim': 'Kadikoy',
        'alanlar': ['Ana Salon'],
        'saatler': {
            'hafta_ici': {'baslangic': '16:00', 'bitis': '22:00'},
            'hafta_sonu': {'baslangic': '12:00', 'bitis': '22:00'}
        }
    },
    'sisli': {
        'isim': 'Sisli',
        'alanlar': ['Buyuk Studyo', 'Kucuk Studyo', 'Perdeli Alan'],
        'saatler': {
            'hafta_ici': {'baslangic': '12:00', 'bitis': '22:00'},
            'hafta_sonu': {'baslangic': '12:00', 'bitis': '22:00'}
        }
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
        return render_template('giris.html', hata='Bu numara kayitli degil')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('giris'))

@app.route('/takvim')
@login_required
def takvim():
    return render_template('takvim.html', isim=session['isim'], admin=session['admin'], studyolar=STUDYOLAR)

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
        cur = conn.cursor()
        cur.execute('SELECT saat, rezerve_eden, telefon, bloklu FROM rezervasyonlar WHERE studyo = %s AND alan = %s AND tarih = %s', (studyo, alan, tarih))
        rezervasyonlar = {row['saat']: row for row in cur.fetchall()}
        cur.close()
        conn.close()
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
        cur = conn.cursor()
        cur.execute('SELECT * FROM rezervasyonlar WHERE studyo = %s AND alan = %s AND tarih = %s AND saat = %s', (studyo, alan, tarih, saat))
        mevcut = cur.fetchone()
        if mevcut:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Bu slot zaten dolu'})
        cur.execute('INSERT INTO rezervasyonlar (studyo, alan, tarih, saat, rezerve_eden, telefon) VALUES (%s, %s, %s, %s, %s, %s)', (studyo, alan, tarih, saat, session['isim'], session['telefon']))
        cur.execute('INSERT INTO aktiviteler (isim, islem, studyo, alan, tarih, saat) VALUES (%s, %s, %s, %s, %s, %s)', (session['isim'], 'rezerve', STUDYOLAR[studyo]['isim'], alan, tarih, saat))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'mesaj': 'Rezervasyon yapildi!'})
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
        cur = conn.cursor()
        cur.execute('SELECT * FROM rezervasyonlar WHERE studyo = %s AND alan = %s AND tarih = %s AND saat = %s', (studyo, alan, tarih, saat))
        mevcut = cur.fetchone()
        if not mevcut:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Rezervasyon bulunamadi'})
        if mevcut['telefon'] != session['telefon'] and not session.get('admin'):
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Bu rezervasyonu iptal edemezsiniz'})
        cur.execute('DELETE FROM rezervasyonlar WHERE studyo = %s AND alan = %s AND tarih = %s AND saat = %s', (studyo, alan, tarih, saat))
        cur.execute('INSERT INTO aktiviteler (isim, islem, studyo, alan, tarih, saat) VALUES (%s, %s, %s, %s, %s, %s)', (session['isim'], 'iptal', STUDYOLAR[studyo]['isim'], alan, tarih, saat))
        conn.commit()
        cur.close()
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
        cur = conn.cursor()
        cur.execute('SELECT * FROM aktiviteler ORDER BY created_at DESC LIMIT 30')
        aktiviteler = []
        for row in cur.fetchall():
            created = row['created_at']
            now = datetime.now()
            diff = now - created
            if diff.seconds < 60:
                zaman = 'Az once'
            elif diff.seconds < 3600:
                zaman = f'{diff.seconds // 60} dakika once'
            elif diff.seconds < 86400:
                zaman = f'{diff.seconds // 3600} saat once'
            else:
                zaman = f'{diff.days} gun once'
            aktiviteler.append({'isim': row['isim'], 'islem': row['islem'], 'studyo': row['studyo'], 'alan': row['alan'], 'tarih': row['tarih'].strftime('%Y-%m-%d'), 'saat': row['saat'], 'zaman': zaman})
        cur.close()
        conn.close()
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
        islem = data['islem']
        gun_map = {'Pzt': 0, 'Sal': 1, 'Car': 2, 'Per': 3, 'Cum': 4, 'Cmt': 5, 'Paz': 6}
        if 'hepsi' in gunler:
            secili_gunler = [0, 1, 2, 3, 4, 5, 6]
        else:
            secili_gunler = [gun_map[g] for g in gunler if g in gun_map]
        saatler = saat_listesi_olustur(saat_bas, saat_bit)
        conn = get_db()
        cur = conn.cursor()
        bugun = datetime.now().date()
        islem_sayisi = 0
        for i in range(90):
            tarih = bugun + timedelta(days=i)
            if tarih.weekday() in secili_gunler:
                for saat in saatler:
                    tarih_str = tarih.strftime('%Y-%m-%d')
                    if islem == 'blokla':
                        cur.execute('INSERT INTO rezervasyonlar (studyo, alan, tarih, saat, bloklu) VALUES (%s, %s, %s, %s, TRUE) ON CONFLICT (studyo, alan, tarih, saat) DO UPDATE SET bloklu = TRUE, rezerve_eden = NULL, telefon = NULL', (studyo, alan, tarih_str, saat))
                    else:
                        cur.execute('DELETE FROM rezervasyonlar WHERE studyo = %s AND alan = %s AND tarih = %s AND saat = %s AND bloklu = TRUE', (studyo, alan, tarih_str, saat))
                    islem_sayisi += 1
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'mesaj': f'{islem_sayisi} slot guncellendi'})
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
