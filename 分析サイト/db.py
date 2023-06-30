import sqlite3

con = sqlite3.connect("data.db")
cur = con.cursor()
cur.execute("""
            CREATE TABLE USERS(id INTEGER PRIMARY KEY AUTOINCREMENT,
                               name STRING,
                               email STRING,
                               password STRING)
            """)
con.commit()
con.close()