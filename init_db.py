import sqlite3

def initialize_database():
    conn = sqlite3.connect('equipment.db')
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        available BOOLEAN NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS similar_items (
        item_id INTEGER,
        similar_item_id INTEGER,
        FOREIGN KEY (item_id) REFERENCES equipment(id),
        FOREIGN KEY (similar_item_id) REFERENCES equipment(id)
    )
    ''')

    # Insert dummy data
    cursor.execute("DELETE FROM equipment")
    cursor.execute("DELETE FROM similar_items")

    cursor.executemany("INSERT INTO equipment (name, category, price, available) VALUES (?, ?, ?, ?)", [
        ('Canon EOS R5', 'Camera', 150.00, 1),
        ('Sony A7III', 'Camera', 120.00, 1),
        ('DJI Ronin-S', 'Stabilizer', 50.00, 1),
        ('Aputure 120d II', 'Lighting', 75.00, 0),
        ('Rode NTG3', 'Audio', 40.00, 1)
    ])

    cursor.executemany("INSERT INTO similar_items (item_id, similar_item_id) VALUES ((SELECT id FROM equipment WHERE name = ?), (SELECT id FROM equipment WHERE name = ?))", [
        ('Canon EOS R5', 'Sony A7III'),
        ('Sony A7III', 'Canon EOS R5'),
        ('Aputure 120d II', 'Rode NTG3')
    ])

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_database()