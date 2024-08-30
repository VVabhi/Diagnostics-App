from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length
from pymongo import MongoClient
from wtforms import StringField, PasswordField, SubmitField
from bson import ObjectId
import json
import datetime
from docx import Document
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'

client = MongoClient("mongodb://localhost:27017/")
db = client['DIAGNOSTICS']
employees_collection = db['employeesCollection']
patient_collection = db['patients']


inventory_collection = db['inventory']
store_inventory_collection = db['Store_inventory']
tests_collection = db['tests']  # Collection for storing test information


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    employee_name = StringField('Employee Name', validators=[DataRequired(), Length(min=2, max=50)])
    employee_id = StringField('Employee ID', validators=[DataRequired(), Length(min=2, max=50)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=100)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=30)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=30)])
    submit = SubmitField('Register')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        employee = employees_collection.find_one({'username': username, 'password': password})

        if employee:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', form=form, error="Invalid credentials")

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        employee_name = form.employee_name.data
        employee_id = form.employee_id.data
        phone_number = form.phone_number.data  # New field
        address = form.address.data  # New field
        username = form.username.data
        password = form.password.data

        employee_data = {
            'employee_name': employee_name,
            'employee_id': employee_id,
            'phone_number': phone_number,
            'address': address,  
            'username': username,
            'password': password,
        }

        employees_collection.insert_one(employee_data)
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']
        employee = employees_collection.find_one({'username': username})
        return render_template('dashboard.html', employee=employee)
    else:
        return redirect(url_for('login'))


@app.route('/new_test')
def new_test():
    if 'username' in session:
        # Fetch tests from the collection
        tests = list(tests_collection.find({}, {'_id': 0, 'test_name': 1, 'cost': 1}))
        return render_template('new_test.html', tests=tests)
    else:
        return redirect(url_for('login'))

@app.route('/input')
def input_page():
    if 'username' in session:
        tests = list(tests_collection.find({}, {'_id': 0, 'test_name': 1, 'cost': 1}))
        return render_template('input.html', tests=tests)
    else:
        return redirect(url_for('login'))


@app.route('/add_test', methods=['POST'])
def add_test():
    if 'username' in session:
        test_name = request.form.get('testName')
        sample_type = request.form.get('sampleType')
        cost = request.form.get('cost')
        report_format = request.form.get('reportFormat')

        # Initialize the report_units based on the selected report format
        report_units = None

        if report_format == 'table':
            # Collect the table data from the form
            report_units = []
            index = 1
            while True:
                parameter = request.form.get(f'parameter{index}')
                reference = request.form.get(f'reference{index}')
                units = request.form.get(f'units{index}')
                if parameter and reference and units:
                    report_units.append({
                        'parameter': parameter,
                        'reference': reference,
                        'units': units
                    })
                    index += 1
                else:
                    break

        elif report_format == 'textarea':
            # Collect the textarea data from the form
            report_units = request.form.get('reportUnits')

        # Ensure the necessary values are not None
        if test_name and sample_type and cost and report_format and report_units is not None:
            new_test = {
                'test_name': test_name,
                'sample_type': sample_type,
                'cost': float(cost),
                'report_format': report_format,
                'report_units': report_units  # Store either the table data or the textarea content
            }

            tests_collection.insert_one(new_test)  # Insert into the correct collection
            print(f"Received: {test_name}, {sample_type}, {cost}, {report_format}")
            return redirect(url_for('new_test'))
        else:
            return "Error: Missing data", 400
    else:
        return redirect(url_for('login'))


@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    patientName = data.get('patientName')
    phoneNumber = data.get('phoneNumber')
    age = data.get('age')
    sex = data.get('sex')
    refBy = data.get('refBy')
    date = data.get('date')
    test = data.get('test')
    otherTest = data.get('otherTest')
    sampleType = data.get('sampleType')
    cost = data.get('cost')
    modeOfPayment = data.get('modeOfPayment')

    patient_data = {
        'patient_name': patientName,
        'phone_number': phoneNumber,
        'age': age,
        'sex': sex,
        'ref_by': refBy,
        'date': date,
        'test': test,
        'other_test': otherTest,
        'sampleType': sampleType,
        'cost': cost,
        'mode_of_payment': modeOfPayment
    }

    patient_collection.insert_one(patient_data)
    return jsonify({"message": "Patient details added successfully!"}), 201


@app.route('/display')
def display():
    if 'username' in session:
        patients = list(patient_collection.find())
        tests = list(tests_collection.find())  # Fetch all tests
        
        # Convert ObjectId to string for JSON serialization
        for patient in patients:
            patient['_id'] = str(patient['_id'])
        
        for test in tests:
            test['_id'] = str(test['_id'])  # Ensure the ObjectId is converted to string
            if isinstance(test['report_units'], list):
                for unit in test['report_units']:
                    if isinstance(unit, dict):
                        for k, v in unit.items():
                            if isinstance(v, ObjectId):
                                unit[k] = str(v)
            elif isinstance(test['report_units'], ObjectId):
                test['report_units'] = str(test['report_units'])
        
        # Render the template with patients and tests data
        return render_template('details.html', patients=patients, tests=tests)
    else:
        return redirect(url_for('login'))

@app.route('/generate_report', methods=['POST'])
def generate_report():
    data = request.get_json()
    patient_id = data.get('patient_id')
    report_data = data.get('report')

    if isinstance(report_data, dict):  # Structured report (table format)
        structured_report = {}
        for param, value in report_data.items():
            structured_report[param] = {
                'value': value.get('value', ''),
                'reference': value.get('reference', ''),
                'units': value.get('units', '')
            }
    elif isinstance(report_data, str):  # Plain text report
        structured_report = report_data
    else:
        return jsonify({"message": "Invalid report data."}), 400

    # Update patient record in MongoDB
    patient_collection.update_one(
        {'_id': ObjectId(patient_id)},
        {'$set': {'report': structured_report, 'additional_notes': data.get('additional_notes', '')}}
    )

    return jsonify({"message": "Report updated successfully!"}), 200


@app.route('/reports')
def reports_page():
    if 'username' in session:
        patients_list = list(patient_collection.find({'report': {'$exists': True}}))
        return render_template('reports.html', patients=patients_list)
    else:
        return redirect(url_for('login'))

@app.route('/patients')
def patients_page():
    if 'username' in session:
        patients_list = list(patient_collection.find())
        return render_template('patients.html', patients=patients_list, enumerate=enumerate)
    else:
        return redirect(url_for('login'))

@app.route('/update_patient', methods=['POST'])
def update_patient():
    if 'username' in session:
        try:
            patient_id = request.form.get('patient_id')
            updated_data = {
                'patient_name': request.form.get('patient_name'),
                'age': request.form.get('age'),
                'test': request.form.get('test'),
                'date': request.form.get('dob'),
            }
            result = patient_collection.update_one({'_id': ObjectId(patient_id)}, {'$set': updated_data})

            if result.modified_count > 0:
                return redirect(url_for('patients_page', success='updated'))
            else:
                return redirect(url_for('patients_page', error='no_update'))
        except Exception as e:
            return redirect(url_for('patients_page', error=str(e)))
    else:
        return redirect(url_for('login'))
    
@app.route('/tests')
def tests_page():
    if 'username' in session:
        tests = list(tests_collection.find({}))  # Fetch all tests from the collection
        return render_template('tests.html', tests=tests, enumerate=enumerate)
    else:
        return redirect(url_for('login'))


@app.route('/update_test', methods=['POST'])
def update_test():
    if 'username' in session:
        test_id = request.form.get('test_id')
        test_name = request.form.get('test_name')
        cost = request.form.get('cost')

        tests_collection.update_one(
            {'_id': ObjectId(test_id)},
            {'$set': {
                'test_name': test_name,
                'cost': float(cost)
            }}
        )

        return redirect(url_for('tests_page'))
    else:
        return redirect(url_for('login'))

@app.route('/employees')
def employees_page():
    if 'username' in session:
        employees_list = list(employees_collection.find())
        return render_template('employees.html', employees=employees_list, enumerate=enumerate)
    else:
        return redirect(url_for('login'))


@app.route('/update_employee', methods=['POST'])
def update_employee():
    if 'username' in session:
        employee_id = request.form.get('employee_id')
        employee_name = request.form.get('employee_name')
        employee_id_number = request.form.get('employee_id_number')
        username = request.form.get('username')

        updated_data = {
            'employee_name': employee_name,
            'employee_id': employee_id_number,
            'username': username,
        }

        result = employees_collection.update_one({'_id': ObjectId(employee_id)}, {'$set': updated_data})

        if result.modified_count > 0:
            return jsonify({"message": "Employee updated successfully!", "success": True})
        else:
            return jsonify({"message": "No changes made.", "success": False})
    else:
        return jsonify({"message": "You are not logged in.", "success": False})



@app.route('/payments')
def payments_page():
    if 'username' in session:
        date_filter = request.args.get('date')
        query = {}
        if date_filter:
            query['date'] = date_filter

        payments_list = list(patient_collection.find(query, {'patient_name': 1, 'cost': 1, 'mode_of_payment': 1, 'date': 1}))

        # Convert ObjectId to string
        for payment in payments_list:
            payment['_id'] = str(payment['_id'])

        total_costs = {'cash': 0, 'upi': 0, 'card': 0}
        for payment in payments_list:
            mode_of_payment = payment.get('mode_of_payment')
            if mode_of_payment:
                mode_of_payment = mode_of_payment.lower()
                if mode_of_payment in total_costs:
                    total_costs[mode_of_payment] += float(payment.get('cost', 0))

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'payments': payments_list,
                'total_costs': total_costs
            })

        return render_template('payments.html', payments=payments_list, total_costs=total_costs)
    else:
        return redirect(url_for('login'))


@app.route('/inventory', methods=['GET', 'POST'])
def inventory_page():
    if 'username' in session:
        if request.method == 'POST':
            if request.is_json:
                inventory_list = list(inventory_collection.find({}, {'_id': 0}))  
                return jsonify(inventory_list)
            else:
                name = request.form['name']
                apperatus = request.form['apperatus']
                quantity = request.form['quantity']
                supplier = request.form['supplier']
                cost = request.form['cost']
                payment_date = request.form['payment_date']

                inventory_data = {
                    'name': name,
                    'apperatus': apperatus,
                    'quantity': quantity,
                    'supplier': supplier,
                    'cost': cost,
                    'payment_date': payment_date
                }

                inventory_collection.insert_one(inventory_data)
                return redirect(url_for('inventory_page'))

        inventory_list = list(inventory_collection.find())
        return render_template('inventory.html', inventory=inventory_list)
    else:
        return redirect(url_for('login'))
    
@app.route('/store_inventory', methods=['GET', 'POST'])
def store_inventory_page():
    if 'username' in session:
        if request.method == 'POST':
            apparatus_name = request.form['apparatusName']
            quantity = request.form['quantity']

            # Separate the numeric part and the unit part of the quantity
            quantity_value = ''.join(filter(str.isdigit, quantity))
            quantity_unit = ''.join(filter(str.isalpha, quantity))

            if not quantity_value or not quantity_unit:
                return "Invalid quantity input. Please enter a valid quantity with units (e.g., 25L, 20Kg).", 400

            try:
                quantity_value = int(quantity_value)

                # Check if the apparatus already exists in the collection
                existing_item = store_inventory_collection.find_one({'apparatus_name': apparatus_name})

                if existing_item:
                    # If it exists, update the quantity
                    existing_quantity_value = int(''.join(filter(str.isdigit, existing_item['quantity'])))
                    updated_quantity_value = existing_quantity_value + quantity_value
                    updated_quantity = f"{updated_quantity_value}{quantity_unit}"
                    store_inventory_collection.update_one(
                        {'_id': existing_item['_id']},
                        {'$set': {'quantity': updated_quantity}}
                    )
                else:
                    # If it doesn't exist, insert a new document
                    store_inventory_data = {
                        'apparatus_name': apparatus_name,
                        'quantity': quantity
                    }
                    store_inventory_collection.insert_one(store_inventory_data)

                return redirect(url_for('store_inventory_page'))
            except ValueError:
                # Handle invalid quantity input
                return "Invalid quantity input. Please enter a valid number.", 400

        inventory_list = list(store_inventory_collection.find())
        return render_template('store_inventory.html', inventory=inventory_list)
    else:
        return redirect(url_for('login'))
    



@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
