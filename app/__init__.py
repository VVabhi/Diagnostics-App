from flask import Flask
from pymongo import MongoClient
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = 'your_secret_key'

client = MongoClient("mongodb://localhost:27017/")
db = client['DIAGNOSTICS']
employees_collection = db['employeesCollection']
patient_collection = db['patients']
inventory_collection = db['inventory']
store_inventory_collection = db['Store_inventory']

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    employee_name = StringField('Employee Name', validators=[DataRequired()])
    employee_id = StringField('Employee ID', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

from app import routes  # Import routes after app initialization
