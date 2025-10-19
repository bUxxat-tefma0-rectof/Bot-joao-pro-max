import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('shop_bot.db', check_same_thread=False)
        self.create_tables()

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
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referred_by) REFERENCES users (user_id)
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
                FOREIGN KEY (product_id) REFERENCES products (product_id)
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
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (used_by) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()

    # Métodos para usuários
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

    def create_user(self, user_id, username, affiliate_code=None, referred_by=None):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, affiliate_code, referred_by)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, affiliate_code, referred_by))
            self.conn.commit()
            return True
        except:
            return False

    def update_user_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()

    # Métodos para produtos
    def get_products(self, category='premium'):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE category = ? AND is_active = TRUE', (category,))
        return cursor.fetchall()

    def get_product(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        return cursor.fetchone()

    def update_product_stock(self, product_id, quantity):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (quantity, product_id))
        self.conn.commit()

    def increment_product_sales(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE products SET sales_count = sales_count + 1 WHERE id = ?', (product_id,))
        self.conn.commit()

    # Métodos para pedidos
    def create_order(self, user_id, product_id, quantity, total_price, credentials):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO orders (user_id, product_id, quantity, total_price, credentials)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, product_id, quantity, total_price, credentials))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_orders(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT o.*, p.name 
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            WHERE o.user_id = ?
            ORDER BY o.order_date DESC
        ''', (user_id,))
        return cursor.fetchall()

    # Métodos para ranking
    def get_top_products(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT name, sales_count 
            FROM products 
            ORDER BY sales_count DESC 
            LIMIT 10
        ''')
        return cursor.fetchall()

    def get_top_rechargers(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.username, SUM(r.amount) as total_recharged
            FROM recharges r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.status = 'completed'
            AND strftime('%m', r.recharge_date) = strftime('%m', 'now')
            GROUP BY r.user_id
            ORDER BY total_recharged DESC
            LIMIT 10
        ''')
        return cursor.fetchall()

    def get_top_buyers(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.username, COUNT(o.id) as total_purchases
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE strftime('%m', o.order_date) = strftime('%m', 'now')
            GROUP BY o.user_id
            ORDER BY total_purchases DESC
            LIMIT 10
        ''')
        return cursor.fetchall()

    def get_richest_users(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT username, balance 
            FROM users 
            ORDER BY balance DESC 
            LIMIT 10
        ''')
        return cursor.fetchall()

    # Métodos para admin
    def add_product(self, name, description, price, stock, warranty_days=30, category='premium'):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, description, price, stock, warranty_days, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, price, stock, warranty_days, category))
        self.conn.commit()
        return cursor.lastrowid

    def update_product(self, product_id, **kwargs):
        cursor = self.conn.cursor()
        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(product_id)
        cursor.execute(f'UPDATE products SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
