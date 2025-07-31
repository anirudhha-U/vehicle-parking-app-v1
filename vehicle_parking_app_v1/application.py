
#import statements
from flask import Flask, render_template, request, redirect, session, g, url_for, flash
import sqlite3
import os
from datetime import datetime



app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = os.path.join(os.getcwd(), 'database.db')


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db



@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()



@app.route('/')
def home():
    return render_template('home.html')



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        address = request.form['address']
        pin_code = request.form['pin_code']

        db = get_db()
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if existing_user:
            flash('Username already exists.', 'error')
            return render_template('signup.html')

        db.execute("INSERT INTO users (username, password, full_name, address, pin_code, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                   (username, password, full_name, address, pin_code, 0))
        db.commit()
        flash('Signup successful!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash('Login successful!', 'success')

            if user['is_admin']:
                return redirect(url_for('admin_home'))
            else:
                return redirect(url_for('user_home'))
        else:
            flash('Invalid credentials.', 'error')

    return render_template('login.html')




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



# ADMIN ROUTES 



@app.route('/admin/home')
def admin_home():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    db = get_db()
    parking_lots = db.execute("SELECT * FROM Parking_Details").fetchall()
    return render_template('admin-home.html', parking_lots=parking_lots)




@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    db = get_db()
    users = db.execute("SELECT * FROM users WHERE is_admin = 0").fetchall()
    return render_template('admin-user.html', users=users)



@app.route('/admin-search', methods=['GET'])
def admin_search():
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    results = []
    category = request.args.get('category')
    keyword = request.args.get('query', '')

    if category and keyword:  # only search if both are provided
        conn = get_db()
        cursor = conn.cursor()

        base_query = '''
            SELECT u.id AS user_id, u.username, u.full_name, u.address, u.pin_code, 
                   u.is_admin,
                   COALESCE(ph.spot_id, 'N/A') AS spot_id,
                   COALESCE(pd.place_name, 'N/A') AS place_name,
                   COALESCE(ph.status, 'No History') AS parking_status
            FROM users u
            LEFT JOIN Parking_History ph ON u.id = ph.user_id
            LEFT JOIN Parking_Details pd ON ph.spot_id = pd.id
            WHERE 1=1
        '''

        params = []
        if category == 'id':
            base_query += ' AND u.id = ?'
            params.append(keyword)
        elif category == 'fullname':
            base_query += ' AND u.full_name LIKE ?'
            params.append(f'%{keyword}%')
        elif category == 'pincode':
            base_query += ' AND u.pin_code LIKE ?'
            params.append(f'%{keyword}%')
        elif category == 'spot_id':
            base_query += ' AND ph.spot_id = ?'
            params.append(keyword)
        elif category == 'place_name':
            base_query += ' AND pd.place_name LIKE ?'
            params.append(f'%{keyword}%')
        elif category == 'parking_status':
            base_query += ' AND ph.status LIKE ?'
            params.append(f'%{keyword}%')

        base_query += ' ORDER BY ph.park_time DESC'
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        conn.close()

    return render_template('admin-search.html', results=results)




@app.route('/admin/summary')
def admin_summary():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()

   
    total_lots = db.execute("SELECT COUNT(*) FROM Parking_Details").fetchone()[0]

   
    result = db.execute("SELECT SUM(max_spots), SUM(occupied_spots), SUM(available_spots) FROM Parking_Details").fetchone()
    total_spots = result[0] or 0
    total_occupied = result[1] or 0
    total_available = result[2] or 0

    
    total_users = db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0").fetchone()[0]

    
    total_vehicles = db.execute("SELECT COUNT(*) FROM Parking_History WHERE status = 'parked'").fetchone()[0]

    return render_template('admin-summary.html',
        total_lots=total_lots,
        total_spots=total_spots,
        total_occupied=total_occupied,
        total_available=total_available,
        total_users=total_users,
        total_vehicles=total_vehicles
    )



@app.route('/admin/new-parking-lot', methods=['GET', 'POST'])
def new_parking_lot():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        place_name = request.form['place_name']
        address = request.form['address']
        pincode = request.form['pincode']
        max_spots = int(request.form['max_spots'])
        price_per_hour = float(request.form['price_per_hour'])

        db = get_db()
        db.execute("""INSERT INTO Parking_Details (place_name, address, pincode, max_spots, price_per_hour, available_spots, occupied_spots)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (place_name, address, pincode, max_spots, price_per_hour, max_spots, 0))
        db.commit()
        flash('Parking lot added!', 'success')
        return redirect(url_for('admin_home'))
    return render_template('new-parking-lot.html')



@app.route('/admin/edit-parking-lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_parking_lot(lot_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    lot = db.execute("SELECT * FROM Parking_Details WHERE id = ?", (lot_id,)).fetchone()
    if request.method == 'POST':
        place_name = request.form['place_name']
        address = request.form['address']
        pincode = request.form['pincode']
        max_spots = int(request.form['max_spots'])
        price_per_hour = float(request.form['price_per_hour'])
        available_spots = max_spots - lot['occupied_spots']

        db.execute("""UPDATE Parking_Details SET place_name = ?, address = ?, pincode = ?, max_spots = ?, price_per_hour = ?, available_spots = ?
                      WHERE id = ?""",
                   (place_name, address, pincode, max_spots, price_per_hour, available_spots, lot_id))
        db.commit()
        flash('Parking lot updated.', 'success')
        return redirect(url_for('admin_home'))
    return render_template('edit-parking-lot.html', lot=lot)



@app.route('/admin/view-delete-spot/<int:lot_id>', methods=['GET', 'POST'])
def view_delete_spot(lot_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()

    if request.method == 'POST':
        
        lot = db.execute("SELECT * FROM Parking_Details WHERE id = ?", (lot_id,)).fetchone()
        if lot and lot['occupied_spots'] == 0:
            db.execute("DELETE FROM Parking_Details WHERE id = ?", (lot_id,))
            db.commit()
            flash("Parking lot deleted successfully.", "success")
            return redirect(url_for('admin_home'))
        else:
            flash("Cannot delete a parking lot with occupied spots.", "error")
            return redirect(url_for('view_delete_spot', lot_id=lot_id))

   
    spots = db.execute("""
        SELECT * FROM Parking_History 
        WHERE place_name = (SELECT place_name FROM Parking_Details WHERE id = ?)
    """, (lot_id,)).fetchall()

    return render_template('view-delete-spot.html', spots=spots, lot_id=lot_id)




@app.route('/admin/occupied-spot-details/<int:lot_id>')
def occupied_spot_details(lot_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    db = get_db()
    records = db.execute("""SELECT * FROM Parking_History 
                            WHERE place_name = (SELECT place_name FROM Parking_Details WHERE id = ?) AND status = 1""", (lot_id,)).fetchall()
    return render_template('occupied-spot-details.html', records=records)




# USER ROUTES 



@app.route('/user-home')
def user_home():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    history = db.execute("""
        SELECT * FROM Parking_History 
        WHERE user_id = ?
        ORDER BY park_time DESC
    """, (session['user_id'],)).fetchall()

    return render_template('user-home.html', history=history)



@app.route('/release-spot/<int:history_id>', methods=['POST'])
def release_spot(history_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()

    history = db.execute("""
        SELECT * FROM Parking_History 
        WHERE id = ? AND user_id = ?
    """, (history_id, session['user_id'])).fetchone()

    if history and history['status'] == 'parked':
        
        park_time = datetime.strptime(history['park_time'], "%Y-%m-%d %H:%M:%S")
        exit_time = datetime.now()
        exit_time_str = exit_time.strftime("%Y-%m-%d %H:%M:%S")

       
        duration_seconds = (exit_time - park_time).total_seconds()
        duration_minutes = max(5, duration_seconds / 60)    
        hours = duration_minutes / 60

       
        total_cost = round(hours * history['price_per_hour'], 2)

        
        db.execute("""
            UPDATE Parking_History
            SET status = 'parked out',
                exit_time = ?,
                total_cost = ?
            WHERE id = ?
        """, (exit_time_str, total_cost, history_id))

        db.execute("""
            UPDATE Parking_Details
            SET available_spots = available_spots + 1,
                occupied_spots = occupied_spots - 1
            WHERE id = ?
        """, (history['spot_id'],))

        db.commit()
        flash(f"Spot released successfully! Total Cost: ₹{total_cost:.2f}", "success")
    else:
        flash("Invalid release request or already released.", "error")

    return redirect(url_for('user_home'))




@app.route('/user/search', methods=['GET', 'POST'])
def user_search():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    results = []

    if request.method == 'GET':
        category = request.args.get('category')
        query = request.args.get('query')

        if category == 'place_name':
            results = db.execute("SELECT * FROM Parking_Details WHERE place_name LIKE ?", (f'%{query}%',)).fetchall()
        elif category == 'pincode':
            results = db.execute("SELECT * FROM Parking_Details WHERE pincode LIKE ?", (f'%{query}%',)).fetchall()
        elif category == 'address':
            results = db.execute("SELECT * FROM Parking_Details WHERE address LIKE ?", (f'%{query}%',)).fetchall()

    return render_template('user-search.html', results=results)




@app.route('/book-spot/<int:lot_id>', methods=['POST'])
def book_spot(lot_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    vehicle_no = request.form['vehicle_no']
    user_id = session['user_id']
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lot = db.execute("SELECT * FROM Parking_Details WHERE id = ?", (lot_id,)).fetchone()

    if lot and lot['available_spots'] > 0:
       
        db.execute("""
            UPDATE Parking_Details
            SET available_spots = available_spots - 1,
                occupied_spots = occupied_spots + 1
            WHERE id = ?
        """, (lot_id,))


        db.execute("""
            INSERT INTO Parking_History (
                user_id, place_name, address, pincode,
                spot_id, vehicle_no, status,
                park_time, exit_time, price_per_hour
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            lot['place_name'],
            lot['address'],
            lot['pincode'],
            lot['id'],
            vehicle_no,
            'parked',              
            now,
            None,                   
            lot['price_per_hour']
        ))

        db.commit()
        flash("Parking spot booked successfully", "success")
    else:
        flash("No spots available", "error")

    return redirect(url_for('user_search'))



@app.route('/user/summary')
def user_summary():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    summary = db.execute("""
        SELECT 
            COUNT(*) AS total_bookings,
            SUM(total_cost) AS total_spent,
            SUM(CASE WHEN status = 'parked' THEN 1 ELSE 0 END) AS currently_parked
        FROM Parking_History
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    return render_template('user-summary.html', summary=summary)




@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if request.method == 'POST':
        full_name = request.form['full_name']
        address = request.form['address']
        pin_code = request.form['pin_code']

        db.execute("UPDATE users SET full_name = ?, address = ?, pin_code = ? WHERE id = ?",
                   (full_name, address, pin_code, user_id))
        db.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('edit_profile'))

    return render_template('edit-profile.html', user=user)



# RUN

if __name__ == '__main__':
    app.run(debug=True)
