from flask import Flask, render_template, Response, flash, request, redirect, url_for, session,make_response
import cv2
import pickle
import numpy as np
import face_recognition
import cvzone
import datetime
from datetime import time as datetime_time
import time
import threading
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import csv
import io
import logging
import json


# Opening all the necessary files needed 
with open('config.json') as p:
    params = json.load(p)['params']
file = open('Resources/EncodeFile.p', 'rb')
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds


# App configs   
app = Flask(__name__)
app.config['SECRET_KEY'] = 'abc'
app.config['SQLALCHEMY_DATABASE_URI'] = params['sql_url']
db = SQLAlchemy(app)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg',}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Variables defined 
camera = None  # Global variable to store camera object
recognized_students = set()
morn_time = datetime_time(int(params['morning_time']))
even_time = datetime_time(int(params['evening_time']))
curr_time = datetime.datetime.now().time()


# Logic to find what function to call based on the time of day for marking the attendance
if morn_time <= curr_time < even_time:
    morn_attendance = True
    even_attendance = False
else:
    even_attendance = True
    morn_attendance = False


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Models used to connect in SQL Alchemy
# Model of students data table 
class Student_data(db.Model):
    __tablename__ = 'student_data'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    branch = db.Column(db.String(80), unique=True, nullable=False)
    division = db.Column(db.String(80), unique=True, nullable=False)
    regid = db.Column(db.String(80), unique=True, nullable=False)
    rollno = db.Column(db.String(120), unique=True, nullable=False)


# Model of Attendance table 
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.String(20))
    end_time = db.Column(db.String(20))
    date = db.Column(db.Date, default=datetime.date.today)
    roll_no = db.Column(db.String(20), nullable=False)
    division = db.Column(db.String(10))
    branch = db.Column(db.String(100))
    reg_id = db.Column(db.String(100))


# Model of users table 
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    reg_id = db.Column(db.Integer, unique=True)
    psw = db.Column(db.String(128))
    role = db.Column(db.String(100), unique=True)


# Function to start the camera
def start_camera():
    global camera

    if params['camera_type'] == 'webcam':
        camera_index = params['camera_index']
        print("Using webcam at index:", camera_index)
        camera = cv2.VideoCapture(camera_index)
        print("Camera:", camera)
        #host = '127.0.0.1' 
        host = params['host']
    elif params['camera_type'] == 'ip_camera':
        ip_camera_url = params['ip_camera_url']
        print("Using IP camera with URL:", ip_camera_url)
        camera = cv2.VideoCapture(ip_camera_url)
        print("Camera:", camera)
        host = params['host']  # Set host to the value specified in the config file for IP camera
    elif params['camera_type'] == 'usb_cam':
        usb_camera_index = int(params['usb_index'])
        print("Using USB camera at index:", usb_camera_index)
        camera = cv2.VideoCapture(usb_camera_index)
        print("Camera:", camera)
        #host = '127.0.0.1'
        host = params['host']
    else:
        raise ValueError("Invalid camera type specified in config.json")

    return host



# Function to stop the camera
def stop_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None


# Function for comparing incoming face with encoded file
def compare(encodeListKnown, encodeFace):
    matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
    faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
    # print("matches", matches)
    # print("faceDis", faceDis)
    matchIndex = np.argmin(faceDis)
    return matches, faceDis, matchIndex


# Function to get name of student from the index given by comparing function
def get_data(matches, matchIndex, studentIds):
    if matches[matchIndex]:
        student_id = studentIds[matchIndex]  # ID from face recognition
        return student_id
    return None  # Return None if no match found


# Function which writes the morning attendance in the database
def morningattendance(name, current_date, roll_no, div, branch, reg_id):
    time.sleep(2)
    try:
        with app.app_context():
            existing_entry = Attendance.query.filter(
                Attendance.name == name,
                Attendance.date == current_date,
                Attendance.start_time != None
            ).first()

            if existing_entry:
                print("Your Attendance is already recorded before")
            else:
                new_attendance = Attendance(
                    name=name,
                    start_time=datetime.datetime.now().strftime("%H:%M:%S"),
                    date=current_date,
                    roll_no=roll_no,
                    division=div,
                    branch=branch,
                    reg_id=reg_id
                )
                db.session.add(new_attendance)
                db.session.commit()
                print("Start time and student data recorded in the database")
    except Exception as e:
        print("Error:", e)


# Function which writes the evening attendance in the database
def eveningattendance(name, current_date):
    time.sleep(2)
    try:
        with app.app_context():
            existing_entry = Attendance.query.filter(
                Attendance.name == name,
                Attendance.date == current_date,
                Attendance.start_time != None
            ).first()

            if existing_entry:
                existing_entry.end_time = datetime.datetime.now().strftime("%H:%M:%S")
                db.session.commit()
                print("End time recorded in the database")
            else:
                print("No existing entry found for evening attendance")
    except Exception as e:
        print("Error:", e)


# Function which gets data of identified student from the database
def mysqlconnect(student_id):
    # If student_id is None, return None for all values
    if student_id is None:
        return None, None, None, None, None

    try:
        with app.app_context():
            # Query student data using SQLAlchemy
            student_data = Student_data.query.filter_by(
                regid=student_id).first()

            if student_data:
                # If student data is found, extract values
                id = student_data.id
                name = student_data.name
                roll_no = student_data.rollno
                division = student_data.division
                branch = student_data.branch

                return id, name, roll_no, division, branch
            else:
                # If no student is found, return None for all values
                return None, None, None, None, None

    except Exception as e:
        print("Error:", e)
        return None, None, None, None, None


# Function which does the face recognition and displaying the video feed
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
            matches, facedis, matchIndex = compare(encodeListKnown, encodeFace)
            student_id = get_data(matches, matchIndex, studentIds)
            data = mysqlconnect(student_id)
            name = data[1]
            roll_no = data[2]
            div = data[3]
            branch = data[4]
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


# Route of video feed to flask webpage on index page
@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame', content_type='multipart/x-mixed-replace; boundary=frame')


# Route which displays the attendance of all student for that current day
@app.route('/display_attendance', methods=['GET'])
def display_attendance():
    stop_camera()
    try:
        current_date = datetime.datetime.now().date()
        print(current_date)
        data = Attendance.query.filter_by(date=current_date).all()
        return render_template('display_data.html', data=data, current_date=current_date)
    except Exception as e:
        # Return a more informative error message or handle specific exceptions
        return str(e)


# Route to add new studnets page for admins
@app.route('/data')
def data():
    stop_camera()
    return render_template('data.html')


@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form['name']
    branch = request.form['branch']
    division = request.form['division']
    regid = request.form['reg_id']
    rollno = request.form['roll_no']

    # Check if a student with the same name already exists
    existing_student = Student_data.query.filter_by(name=name).first()

    if existing_student:
        # Student already exists, handle the error (e.g., display a message)
        flash('Student already exists!', 'error')
        return redirect(url_for('data'))
    else:
        # Check if the post request has the file part
        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['image']

        # If the user does not select a file, the browser submits an empty file without a filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        # Check if the file extension is allowed
        if file and allowed_file(file.filename):
            # Secure the filename to prevent any malicious activity
            filename = secure_filename(
                regid + '.' + file.filename.rsplit('.', 1)[1].lower())
            # Save the file to the upload folder
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Proceed to add the new student
            user = Student_data(name=name, rollno=rollno,
                                division=division, branch=branch, regid=regid)
            db.session.add(user)
            db.session.commit()
            flash('Student added successfully!', 'success')
            return redirect(url_for('data'))
        else:
            flash(
                'Invalid file extension. Allowed extensions are: png, jpg, jpeg, gif', 'error')
            return redirect(request.url)


# Route for querying the attendace based on filters given for teachers 
@app.route('/get_attendance', methods=['GET'])
def get_attendance():
    stop_camera()
    query_parameters = {}
    for key, value in request.args.items():
        if value:
            query_parameters[key] = value

    if query_parameters:
        attendance_records = Attendance.query.filter_by(
            **query_parameters).all()
        if not attendance_records:
            flash("No records available for the specified criteria")
    else:
        flash("No parameters provided for query")
        attendance_records = []  # Assign an empty list to avoid undefined variable error

    return render_template('results.html', attendance_records=attendance_records)


# Function to download the attendance of particular date in cvs format
@app.route('/download_attendance_csv', methods=['POST'])
def download_attendance_csv():
    try:
        # Assuming the date is submitted via a form
        date = request.form.get('date')
        print(date)
        if not date:
            flash("Date not provided for downloading.")
            return redirect(url_for('get_attendance'))

        # Retrieve attendance records for the specified date
        attendance_records = Attendance.query.filter_by(date=date).all()

        if not attendance_records:
            flash("No attendance records found for the specified date.")
            return redirect(url_for('get_attendance'))

        # Create a CSV string
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Name', 'Start Time', 'End Time', 'Date',
                        'Roll Number', 'Division', 'Branch', 'Registration ID'])
        for record in attendance_records:
            writer.writerow([record.name, record.start_time, record.end_time, record.date,
                            record.roll_no, record.division, record.branch, record.reg_id])

        # Create response
        response = make_response(output.getvalue())
        filename = f"attendance_records_{date}.csv"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-type"] = "text/csv"

        return response
    except Exception as e:
        logging.exception(
            "Error occurred while generating CSV file: %s", str(e))
        flash("An error occurred while generating CSV file.")
        return redirect(url_for('get_attendance'))


# Route to registration page for viewing the attendance
@app.route('/register', methods=['GET', 'POST'])
def register():
    stop_camera()
    error = None  # Initialize error variable
    if request.method == 'POST':
        username = request.form['username']
        reg_id = request.form['reg_id']
        password = request.form['password']
        role = request.form['role']
        # Check if username or reg_id already exists
        existing_user = Users.query.filter_by(username=username).first()
        existing_reg_id = Users.query.filter_by(reg_id=reg_id).first()

        if existing_user:
            error = 'Username already exists!'
        elif existing_reg_id:
            error = 'Registration ID already exists!'
        else:
            # Create new user
            new_user = Users(username=username, reg_id=reg_id,
                             psw=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))

    # Pass error variable to template
    return render_template('register.html', error=error)


# Route to login page 
@app.route('/login', methods=['GET', 'POST'])
def login():
    stop_camera()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Fetch user from the database based on the provided username and password
        user = Users.query.filter_by(username=username, psw=password).first()
        print(user)

        # Check if a user with the provided credentials exists
        if user:
            # Set session variables to track the logged-in user
            session['user_id'] = user.id
            session['username'] = user.username
            # Assuming there's a 'role' attribute for the user
            session['role'] = user.role
            print(session['role'])

            # Redirect based on the user's role
            if user.role == 'admin':
                return redirect(url_for('data'))
            elif user.role == 'teacher':
                return redirect(url_for('get_attendance'))
            elif user.role == 'student':
                return redirect(url_for('display_attendance'))
            else:
                pass

    # Render the login page for GET requests
    return render_template('login.html')


# Function for logout functionality 
@app.route('/logout')
def logout():
    # Clear the session variables
    session.clear()
    # Redirect to the login page
    return redirect(url_for('login'))


# Route to the index page where the camera feed is displayed
@app.route('/')
def index():
    start_camera()
    return render_template('index.html')


# Function to start to the app 
if __name__ == '__main__':
    host = start_camera()  # Determine the camera type and get the host value
    app.run(debug=True, host=host)

