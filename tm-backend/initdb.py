import sqlite3
con = sqlite3.connect('mydatabase.db')
c = con.cursor()
sql = '''
INSERT INTO users (username, phone, role, email, password)
    VALUES ('管理员', '15812345678', 'admin', 'example@example.cn', '$2b$12$6S.75dg0aeWpnu8ZqJso/.fV6QSoe8Qz4WXpkHlTnAeHZq1b1x3n2');
'''
c.execute(sql)
con.commit()
c.close()
con.close()