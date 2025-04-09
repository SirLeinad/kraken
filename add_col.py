import sqlite3
conn = sqlite3.connect("botdata.db")
conn.execute("ALTER TABLE positions ADD COLUMN confidence REAL;")
conn.commit()
conn.close()