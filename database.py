from flask import Flask, render_template, Response, flash, request, redirect, url_for
import cv2
import pickle
import numpy as np
import face_recognition
import cvzone
import sqlite3
import json
import datetime
from datetime import time as datetime_time
import time
import threading
import os
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abc'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/college'
db = SQLAlchemy(app)
camera = cv2.VideoCapture(0)
# camera = cv2.VideoCapture('http://192.168.0.100:8080/video')
file = open('Resources/EncodeFile.p', 'rb')
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds
json_file_path = 'Resources\studentdata.json'

# Create the JSON file if it doesn't exist
if not os.path.exists(json_file_path):
    with open(json_file_path, 'w') as json_file:
        json.dump({}, json_file)
with open(json_file_path, 'r') as json_file:
    student_data = json.load(json_file)

recognized_students = set()
morn_time = datetime_time(20, 0)
even_time = datetime_time(21, 0)
curr_time = datetime.datetime.now().time()
if morn_time <= curr_time < even_time:
    morn_attendance = True
    even_attendance = False
else:
    even_attendance = True
    morn_attendance = False

# Connect to an SQLite database
conn = sqlite3.connect('Database/attendance_database.db')

# Create a cursor object
cursor = conn.cursor()

# Create a table in the database if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY,
        name TEXT,
        start_time TEXT,
        end_time TEXT,
        date DATE,
        roll_no INTEGER,
        div TEXT,
        branch TEXT,
        reg_id TEXT
    )
''')


class Student_data(db.Model):
    __tablename__ = 'student_data'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    branch = db.Column(db.String(80), unique=True, nullable=False)
    division = db.Column(db.String(80), unique=True, nullable=False)
    regid = db.Column(db.String(80), unique=True, nullable=False)
    rollno = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


camera = None  # Global variable to store camera object

# Function to start the camera


def start_camera():
    global camera
    camera = cv2.VideoCapture(0)
    # camera = cv2.VideoCapture('http://192.168.0.100:8080/video')

# Function to stop the camera


def stop_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None


def compare(encodeListKnown, encodeFace):
    matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
    faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
    # print("matches", matches)
    # print("faceDis", faceDis)
    matchIndex = np.argmin(faceDis)
    return matches, faceDis, matchIndex


def get_data(matches, matchIndex, studentIds):
    if matches[matchIndex]:
        student_id = studentIds[matchIndex]  # ID from face recognition
        return student_id
    return None  # Return None if no match found


def morningattendance(name, current_date, roll_no, div, branch, reg_id):
    time.sleep(2)
    # Connect to the SQLite database
    conn = sqlite3.connect('Database/attendance_database.db')
    cursor = conn.cursor()
    # Record start time and date
    start_time = datetime.datetime.now().strftime("%H:%M:%S")
    print("Start time:", start_time)

    # Check if an entry for the person, date, and start time already exists in the database
    cursor.execute("SELECT * FROM attendance WHERE name = ? AND date = ? AND start_time IS NOT NULL",
                   (name, current_date))
    existing_entry = cursor.fetchone()

    if not existing_entry:
        # Insert start time and student data into the attendance database
        cursor.execute("INSERT INTO attendance (name, start_time, date, roll_no, div, branch, reg_id)VALUES"
                       " (?, ?, ?, ?, ?, ?, ?)",
                       (name, start_time, current_date, roll_no, div, branch, reg_id))
        conn.commit()
        print("Start time and student data recorded in the database")
        flash("Your attendance has been recorded", "success")
    else:
        print("Your Attendance is already been recorded before")
    # Close the cursor and database connection
    cursor.close()
    conn.close()


def eveningattendance(name, current_date):
    time.sleep(2)
    # Connect to the SQLite database
    conn = sqlite3.connect('Database/attendance_database.db')
    cursor = conn.cursor()
    # Record end time and date
    end_time = datetime.datetime.now().strftime("%H:%M:%S")
    print("End time:", end_time)

    # Check if an entry for the person, date, and end time already exists in the database
    cursor.execute("SELECT * FROM attendance WHERE name = ? AND date = ? AND end_time IS NOT NULL",
                   (name, current_date))
    existing_entry = cursor.fetchone()

    if not existing_entry:
        # Update the entry with end time
        cursor.execute("UPDATE attendance SET end_time = ? WHERE name = ? AND date = ?",
                       (end_time, name, current_date))
        conn.commit()
        print("End time recorded in the database")
    # Close the cursor and database connection
    cursor.close()
    conn.close()


def gen_frames():
    global camera
    while camera is not None:
        success, frame = camera.read()
        if not success:
            break
        imgS = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches, faceDis, matchIndex = compare(encodeListKnown, encodeFace)
            student_id = get_data(matches, matchIndex, studentIds)
            student_info = student_data.get(student_id, {})
            name = student_info.get('name', '')
            roll_no = student_info.get('roll_no', '')
            div = student_info.get('div', '')
            branch = student_info.get('Branch', '')
            reg_id = student_id  # Use the same ID as "Reg ID"
            print(name)
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
            bbox = x1, y1, x2 - x1, y2 - y1
            imgBackground = cvzone.cornerRect(frame, bbox, rt=0)
            cv2.putText(frame, name, (bbox[0], bbox[1] - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                        (255, 255, 0), 3, lineType=cv2.LINE_AA)
            cv2.putText(imgBackground, reg_id,
                        (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            current_date = datetime.datetime.now().date()
            if student_id and morn_attendance and student_id not in recognized_students:
                t = threading.Thread(target=morningattendance, args=(
                    name, current_date, roll_no, div, branch, reg_id))
                t.start()
                recognized_students.add(student_id)
            if student_id and even_attendance and student_id not in recognized_students:
                t = threading.Thread(
                    target=eveningattendance, args=(name, current_date))
                t.start()
                recognized_students.add(student_id)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame', content_type='multipart/x-mixed-replace; boundary=frame')


@app.route('/display_attendance')
def display_attendance():
    try:
        # Connect to the database
        conn = sqlite3.connect('Database/attendance_database.db')
        cursor = conn.cursor()

        # Execute SQL query to fetch attendance data
        cursor.execute("SELECT * FROM attendance")
        data = cursor.fetchall()

        # Close the cursor and database connection
        cursor.close()
        conn.close()
        return data

    except Exception as e:
        return str(e)


@app.route('/data')
def data():
    stop_camera()
    return render_template('data.html')


@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form['name']
    branch = request.form['branch']
    division = request.form['division']
    regid = request.form['regid']
    rollno = request.form['rollno']

    # Check if a student with the same name already exists
    existing_student = Student_data.query.filter_by(name=name).first()

    if existing_student:
        # Student already exists, handle the error (e.g., display a message)
        flash('Student already exists!', 'error')
        return redirect(url_for('data'))
    else:
        # Student does not exist, proceed to add the new student
        user = Student_data(name=name, rollno=rollno, division=division,
                            branch=branch, regid=regid)
        db.session.add(user)
        db.session.commit()
        flash('Student added successfully!', 'success')
        return redirect(url_for('data'))


@app.route('/')
def index():
    start_camera()
    data = display_attendance()
    return render_template('index.html', data=data)


if __name__ == '__main__':
    app.run(debug=True)
