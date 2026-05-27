import sqlite3
conn = sqlite3.connect('instance/cctv.db')
c = conn.cursor()
# Get list of tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('Tables in cctv.db:', tables)
for table_name in tables:
    if table_name[0] == 'logs':
        print('Found logs table')
        c.execute("PRAGMA table_info(logs)")
        columns = c.fetchall()
        print('Columns:', columns)
        break
else:
    print('Logs table not found')
conn.close()