import sqlite3

con = sqlite3.connect('database.db')
c = con.cursor()

# Creating Users Table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    address TEXT,
    pin_code TEXT,
    is_admin INTEGER NOT NULL CHECK(is_admin IN (0, 1))
)
''')

# Creating Parking Details Table
c.execute('''
CREATE TABLE IF NOT EXISTS Parking_Details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_name TEXT NOT NULL,
    address TEXT NOT NULL,
    pincode TEXT NOT NULL,
    max_spots INTEGER NOT NULL,
    price_per_hour REAL NOT NULL,
    available_spots INTEGER DEFAULT 0,
    occupied_spots INTEGER DEFAULT 0
)
''')

# Creating Parking History Table with user_id and total_cost
c.execute('''
CREATE TABLE IF NOT EXISTS Parking_History (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    place_name TEXT NOT NULL,
    address TEXT NOT NULL,
    pincode TEXT NOT NULL,
    spot_id INTEGER NOT NULL,
    vehicle_no TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('parked', 'parked out')),
    park_time TEXT NOT NULL,
    exit_time TEXT,
    price_per_hour REAL NOT NULL,
    total_cost REAL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (spot_id) REFERENCES Parking_Details(id)
)
''')

# Add default admin user only if not already present
c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
if not c.fetchone():
    c.execute('''
    INSERT INTO users (username, password, full_name, address, pin_code, is_admin)
    VALUES (?, ?, ?, ?, ?, ?)''', ('admin', 'admin', 'System Admin', 'Admin', '000000', 1))

con.commit()
con.close()
print("All tables created successfully.")
