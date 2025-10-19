import sqlite3
import json
from datetime import datetime
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.conn = sqlite3.connect('shop_bot.db', check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
            self.create_tables()
            logger.info("✅ Banco de dados conectado com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar com banco de dados: {e}")
            raise

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                affiliate_code TEXT UNIQUE,
                referred_by INTEGER,
                total_recharged REAL DEFAULT 0.0,
                total_purchases INTEGER DEFAULT 0,
                total_gift_rescued REAL DEFAULT 0.0,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                warranty_days INTEGER DEFAULT 30,
                category TEXT DEFAULT 'premium',
                is_active BOOLEAN DEFAULT TRUE,
                sales_count INTEGER DEFAULT 0
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                total_price REAL,
                status TEXT DEFAULT 'completed',
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                credentials TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # Tabela de recargas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recharges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                stripe_payment_intent_id TEXT,
                recharge_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Tabela de gift cards
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gift_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                amount REAL,
                is_used BOOLEAN DEFAULT FALSE,
                used_by INTEGER,
                used_date TIMESTAMP,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        logger.info("✅ Tabelas criadas com sucesso!")

    # [O RESTANTE DOS MÉTODOS PERMANECE IGUAL...]
