from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import psycopg2
from psycopg2.extras import RealDictCursor
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
    "54173837
