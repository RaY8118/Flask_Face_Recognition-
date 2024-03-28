from flask import Flask, render_template, url_for, request, session, redirect
import pymysql

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abc'
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'college'

# Function to establish a database connection


def get_db_connection():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute a query to check if the user exists
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND psw = %s", (username, password))
        user = cursor.fetchone()

        if user:
            # User authenticated, store user's information in the session
            session['username'] = user[1]
            return redirect(url_for('index'))
        else:
            # Invalid credentials, display an error message
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

# Route to display the registration form


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute a query to insert the new user into the database
        cursor.execute(
            "INSERT INTO users (username, psw) VALUES (%s, %s)", (username, password))
        conn.commit()

        # Close the database connection
        cursor.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


if __name__ == '__main__':
    app.run(debug=True)
