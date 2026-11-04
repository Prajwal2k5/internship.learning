import sqlite3

conn = sqlite3.connect("miniplm.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Database Tables:", cursor.fetchall())

try:
    cursor.execute("SELECT * FROM parts")
    print("Parts Records:", cursor.fetchall())
except sqlite3.Error as e:
    print("Database Error:", e)

conn.close()