import sqlite3
import datetime

class DBManager:
    def __init__(self, db_path='game.db'):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME,
                player1 TEXT,
                player2 TEXT,
                result TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS moves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                move_number INTEGER,
                x INTEGER,
                y INTEGER,
                piece_type INTEGER,
                face INTEGER,
                timestamp DATETIME
            )
        ''')
        conn.commit()
        conn.close()

    def record_game(self, player1, player2):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('INSERT INTO games (start_time, player1, player2) VALUES (?, ?, ?)',
                  (datetime.datetime.now(), player1, player2))
        game_id = c.lastrowid
        conn.commit()
        conn.close()
        return game_id
