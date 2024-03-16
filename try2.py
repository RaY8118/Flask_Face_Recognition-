from flask import Flask, request, jsonify, render_template,flash
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abc'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/college'
db = SQLAlchemy(app)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.String(20))
    end_time = db.Column(db.String(20))
    date = db.Column(db.Date, default=datetime.date.today)
    roll_no = db.Column(db.String(20), nullable=False)
    division = db.Column(db.String(10))
    branch = db.Column(db.String(100))
    reg_id = db.Column(db.String(100))  # Adjusted column name to match the database


@app.route('/get_attendance', methods=['GET'])
def get_attendance():
    query_parameters = {}
    for key, value in request.args.items():
        if value:
            query_parameters[key] = value
    
    if query_parameters:
        attendance_records = Attendance.query.filter_by(**query_parameters).all()
        if not attendance_records:
            flash("No records available for the specified criteria")
    else:
        flash("No parameters provided for query")
        attendance_records = []  # Assign an empty list to avoid undefined variable error
    
    return render_template('results.html', attendance_records=attendance_records)


if __name__ == '__main__':
    app.run(debug=True)
