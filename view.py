from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

# Function to connect to the SQLite database
def connect_db():
    return sqlite3.connect('Database/attendance_database.db')

# Route to display attendance data
@app.route('/display_attendance')
def display_attendance():
    try:
        # Connect to the database
        conn = connect_db()
        cursor = conn.cursor()

        # Execute SQL query to fetch attendance data
        cursor.execute("SELECT * FROM attendance")
        data = cursor.fetchall()

        # Close the cursor and database connection
        cursor.close()
        conn.close()

        # Pass the data to the Jinja template for rendering
        return render_template('display_data.html', data=data)

    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(debug=True)
