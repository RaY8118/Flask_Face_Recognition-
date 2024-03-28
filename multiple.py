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
import pymysql

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abc'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/college'
db = SQLAlchemy(app)
file = open('Resources/EncodeFile.p', 'rb')
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds

# Define multiple video sources (replace these with your actual video sources)
video_sources = [
    0,
    'http://192.168.254.37:8080/video'
]
current_source_index = 0  # Index of the currently selected video source

# Function to switch between video sources


def switch_video_source():
    global current_source_index
    current_source_index = (current_source_index + 1) % len(video_sources)


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


def mysqlconnect(student_id):
    # If student_id is None, return None for all values
    if student_id is None:
        return None, None, None, None, None

    # To connect MySQL database
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password="",
        db='college',
    )

    cur = conn.cursor()

    try:
        # Select query
        cur.execute("SELECT * FROM student_data WHERE regid = %s",
                    (student_id,))
        output = cur.fetchall()

        for i in output:
            id = i[0]
            name = i[1]
            roll_no = i[2]
            division = i[3]
            branch = i[4]

        # To close the connection
        conn.close()
        return id, name, roll_no, division, branch

    except Exception as e:
        print("Error:", e)
        return None, None, None, None, None


# Function to generate video frames from the current video source
def gen_frames():
    # Open video stream from the current video source
    camera = cv2.VideoCapture(video_sources[current_source_index])
    while True:
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

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/switch_video', methods=['POST'])
def switch_video():
    switch_video_source()
    return 'Switched video source successfully'


@app.route('/')
def index():
    return render_template('multiple.html')


if __name__ == '__main__':
    app.run(debug=True , host='192.168.254.176')
