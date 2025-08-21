import sqlite3

conn = sqlite3.connect('calender.db')

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS calender_events (
    name_of_event TEXT NOT NULL,
    date TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    participants TEXT NOT NULL)
               """)

conn.execute("""
             INSERT INTO calender_events (name_of_event, date, duration_minutes, participants)
             VALUES ('Team Meeting', '2023-10-01T10:00:00', 60, 'Alice,Bob,Charlie')
             """)

conn.commit()
cursor.execute("""SELECT * FROM calender_events""")

for row in cursor.fetchall():
    print(row)

conn.close()
    