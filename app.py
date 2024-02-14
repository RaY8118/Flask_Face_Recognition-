from flask import Flask, render_template, Response
import cv2
import pickle
import numpy as np
import face_recognition
import cvzone

app=Flask(__name__)
webcam = True
ip_cam = False
if webcam:
    camera = cv2.VideoCapture(0)
elif ip_cam:
    camera = cv2.VideoCapture('http://192.168.0.100:8080/video')
else:
    print("Couldnt find a source")
    
file = open('Resources/EncodeFile.p', 'rb')
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds

def gen_frames():  
    while True:
        success, frame = camera.read()
        imgS = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)
        k = cv2.waitKey(1)

        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            # print("matches", matches)
            # print("faceDis", faceDis)
            matchIndex = np.argmin(faceDis)

            if matches[matchIndex]:
                # print("Known face detected")
                student_id = studentIds[matchIndex]  # ID from face recognition
                print(student_id)
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                bbox = x1, y1, x2 - x1, y2 - y1
                frame= cvzone.cornerRect(frame, bbox, rt=0)
                cv2.putText(frame, student_id, (bbox[0], bbox[1] - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                            (255, 255, 0), 3, lineType=cv2.LINE_AA)
            
        if k == ord('q'):
            break
        cv2.waitKey(1)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
     
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
if __name__ == "__main__":
    app.run(debug=True, port=5000)
