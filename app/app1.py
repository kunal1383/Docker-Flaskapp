from flask import Flask, request, render_template, flash, redirect, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
import yaml
from functools import wraps
from flask_socketio import SocketIO
import os

app = Flask(__name__)

#configure db
db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'Hostel'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql=MySQL(app)
# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap
@app.route('/')
def index():
    return render_template('home.html')

#RegisterForm
class RegisterForm(Form):
    student_recepit= StringField('Recepit No', [validators.Length(min=1, max=10)])
    name = StringField('Name', [validators.Length(min=1, max=50)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')
#singup
@app.route('/signup', methods=['GET', 'POST'])

def signup():
    form = RegisterForm(request.form)
    if request.method == 'POST':
        student_recepit = request.form['student_recepit' ]
        cur = mysql.connection.cursor()
         #get user name
        result = cur.execute("SELECT *FROM student WHERE recepit_no = %s",[student_recepit])
        if result > 0:
            # get stored hash
            data = cur.fetchone()
            recepit =data['recepit_no']

            #compare Passwords
            if student_recepit == recepit and form.validate():
            
                flash('recepit verified')
                student_recepit = form.student_recepit.data
                name = form.name.data
                email = form.email.data
                password = sha256_crypt.encrypt(str(form.password.data))

                #cursor
                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO student_users(student_recepit,name, email, password) VALUES(%s,%s, %s, %s)",(student_recepit,name, email, password))
                mysql.connection.commit()
                cur.close()
                flash('Registerd','success')
                return redirect(url_for('login1'))
        else:
            error = 'Invalid Recepit No'
            return render_template('signup.html', form=form,error=error,title='SignUp')

    return render_template('signup.html', form=form,title='SignUp')
#Login
@app.route('/login',methods=['GET', 'POST' ])

def login():
    if request.method == 'POST' :
        #get form fields
        name = request.form['name' ]
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()
         #get user name
        result = cur.execute("SELECT *FROM users WHERE name = %s",[name])

        if result > 0:
            # get stored hash
            data = cur.fetchone()
            password =data['password']

            #compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                #passed
                session['logged_in'] = True
                session['name'] = name

                flash('You are now logged in')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid password'
                return render_template('login.html',error=error,title='Login')
            cur.close()
        else:
            error = 'User name not found'
            return render_template('login.html',error=error,title='Login')

    return render_template('login.html',title='Login')


#logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have logged out','success')
    return redirect(url_for('login'))
#dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():

    cur=mysql.connection.cursor()
    result = cur.execute("SELECT *FROM student")
    students = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html',students=students,title='Dashboard')
    else:
        msg = 'No Entry'
        return render_template('dashboard.html',msg=msg,title='Dashboard')
    cur.close()

#student form
class StudentForm(Form):

    name = StringField('Name', [validators.Length(min=1, max=50)])
    contact_no = StringField('Contact', [validators.Length(min=10,max=10)])
    room_no = StringField('Room No', [validators.Length(min=3)])
    recepit_no = StringField('Recepit No', [validators.Length(min=1,max=10)])

# add student entry
@app.route('/add_student', methods = ['GET', 'POST'])
@is_logged_in
def add_student():

    form = StudentForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        contact_no = form.contact_no.data
        room_no = form.room_no.data
        recepit_no = form.recepit_no.data

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO student( name, contact_no, room_no, recepit_no) VALUES(%s,%s,%s,%s)",( name, contact_no, room_no, recepit_no))

        mysql.connection.commit()

        cur.close()
        flash('Entry added','success')

        return redirect(url_for('dashboard',title='Dashboard'))
    return render_template('add_student.html',form=form)

# edit student entry
@app.route('/edit_student/<string:student_id>', methods = ['GET', 'POST'])
@is_logged_in
def edit_student(student_id):

    #cursor
    cur=mysql.connection.cursor()
     #app.logger.info(name)
    result = cur.execute("SELECT *FROM student WHERE student_id=%s",[student_id])
    student = cur.fetchone()
#GET FORM
    form = StudentForm(request.form)
    #Populate student field
    form.name.data = student['name']
    form.contact_no.data = student['contact_no']
    form.room_no.data = student['room_no']
    form.recepit_no.data = student['recepit_no']

    if request.method == 'POST' and form.validate():
        name = request.form['name' ]
        contact_no =  request.form['contact_no' ]
        room_no =  request.form['room_no' ]
        recepit_no =  request.form['recepit_no' ]

        cur = mysql.connection.cursor()
        cur.execute("UPDATE student SET name=%s, contact_no=%s, room_no=%s, recepit_no=%s where student_id=%s",(name,contact_no,room_no,recepit_no,student_id))

        mysql.connection.commit()

        cur.close()
        flash('Entry edited successfully','success')

        return redirect(url_for('dashboard'))
    return render_template('edit_student.html',form=form)

#delete student entry
@app.route('/delete_student/<string:id>',methods=['POST'])
@is_logged_in
def delete_student(id):
    cur=mysql.connection.cursor()
    cur.execute("DELETE FROM student where student_id=%s",[id])
    mysql.connection.commit()

    cur.close()
    flash('Entry Deleted','success')

    return redirect(url_for('dashboard'))


#student login/signup
@app.route('/student')
def student():
    return render_template('student.html')


#Login for student
@app.route('/login1',methods=['GET', 'POST' ])

def login1():
    if request.method == 'POST' :
        #get form fields
        student_recepit = request.form['student_recepit' ]
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()
         #get user name
        result = cur.execute("SELECT *FROM student_users WHERE student_recepit = %s",[student_recepit])

        if result > 0:
            # get stored hash
            data = cur.fetchone()
            password =data['password']

            #compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                #passed
                session['logged_in'] = True
                session['student_recepit'] = student_recepit

                flash('You are now logged in')
                return redirect(url_for('dashboard1'))
            else:
                error = 'Invalid password'
                return render_template('login1.html',error=error,title='Login')
            cur.close()
        else:
            error = 'Invalid Recepit No'
            return render_template('login1.html',error=error,title='Login')

    return render_template('login1.html',title='Login')

class ProblemForm(Form):
    
    room_no = StringField('room_no', [validators.Length(min=4,max=6)])   
    problem_title = StringField('Problem title', [validators.Length(min=1, max=20)])
    problem = StringField('Problem', [validators.Length(min=1,max=100)])
    
    

@app.route('/problem', methods = ['GET', 'POST'])
@is_logged_in
def problem_dash():
    form2 = ProblemForm(request.form)
    if request.method == 'POST' and form2.validate():
        room_no = form2.room_no.data
        problem_title = form2.problem_title.data
        problem = form2.problem.data
        student_reciept=session['student_recepit']
        
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO problem(recepit_no, room_no,problem_title,problem) VALUES(%s,%s,%s,%s)",( student_reciept,room_no ,problem_title,problem))
        mysql.connection.commit()

        cur.close()
        flash('problem sent','success')

        return redirect(url_for('dashboard1'))
    return render_template('problem.html',form2=form2)

@app.route('/show_problem', methods = ['GET', 'POST'])
@is_logged_in
def dashboard2():

    cur=mysql.connection.cursor()
    result = cur.execute("SELECT *FROM problem")
    problem = cur.fetchall()

    if result > 0:
        return render_template('show_problem.html',problem=problem,title='Dashboard2')
    else:
        msg = 'No Entry'
        return render_template('show_problem.html',msg=msg,title='Dashboard2')
    cur.close()

@app.route('/change_status/<string:recepit_no>',methods=['GET','POST'])
@is_logged_in
def change_status(recepit_no):
    cur=mysql.connection.cursor()
    cur.execute("UPDATE problem SET status =1 WHERE recepit_no=%s",[recepit_no])
    mysql.connection.commit()

    cur.close()
    #flash('','success')

    return redirect(url_for('dashboard2'))



class MenuForm(Form):

    day = StringField('Day', [validators.Length(min=1, max=50)])
    breakfast = StringField('Breakfast', [validators.Length(min=1,max=50)])
    lunch = StringField('Lunch', [validators.Length(min=1,max=50)])
    dinner = StringField('Dinner', [validators.Length(min=1,max=50)])
#MEnu
    @app.route('/menu', methods = ['GET', 'POST'])
    @is_logged_in
    def menu():

        form1 = MenuForm(request.form)
        if request.method == 'POST' and form1.validate():
            day = form1.day.data
            breakfast = form1.breakfast.data
            lunch = form1.lunch.data
            dinner = form1.dinner.data

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO menu( day, breakfast, lunch, dinner) VALUES(%s,%s,%s,%s)",( day, breakfast, lunch, dinner))

            mysql.connection.commit()

            cur.close()
            flash('Menu added','success')

            return redirect(url_for('menu_dash'))
        return render_template('menu.html',form1=form1)


#menu dashboard
@app.route('/menu_dash')

def menu_dash():

    cur=mysql.connection.cursor()
    result = cur.execute("SELECT *FROM menu")
    menus = cur.fetchall()

    if result > 0:
        return render_template('menu_dash.html',menus=menus)
    else:
        msg = 'No Entry'
        return render_template('menu_dash.html',msg=msg)
    cur.close()
#edit menu

@app.route('/edit_menu/<string:menu_id>', methods = ['GET', 'POST'])
@is_logged_in
def edit_menu(menu_id):

    #cursor
    cur=mysql.connection.cursor()
     #app.logger.info(name)
    result = cur.execute("SELECT *FROM menu WHERE menu_id=%s",[menu_id])
    menu = cur.fetchone()
#GET FORM
    form1 = MenuForm(request.form)
    #Populate student field
    form1.day.data = menu['day']
    form1.breakfast.data = menu['breakfast']
    form1.lunch.data = menu['lunch']
    form1.dinner.data = menu['dinner']

    if request.method == 'POST' and form1.validate():
        day = request.form['day' ]
        breakfast =  request.form['breakfast' ]
        lunch =  request.form['lunch' ]
        dinner =  request.form['dinner' ]

        cur = mysql.connection.cursor()
        cur.execute("UPDATE menu SET day=%s, breakfast=%s, lunch=%s, dinner=%s where menu_id=%s",(day,breakfast,lunch,dinner,menu_id))

        mysql.connection.commit()

        cur.close()
        flash('Menu edited successfully','success')

        return redirect(url_for('menu_dash'))
    return render_template('edit_menu.html',form1=form1)


#delete_menu
@app.route('/delete_menu/<string:id>',methods=['POST'])
@is_logged_in
def delete_menu(id):

    cur=mysql.connection.cursor()
    cur.execute("DELETE FROM menu where menu_id=%s",[id])
    mysql.connection.commit()

    cur.close()
    flash('Entry Deleted','success')

    return redirect(url_for('menu_dash'))


#dashbord for students
@app.route('/dashboard1')

def dashboard1():

    cur=mysql.connection.cursor()
    result = cur.execute("SELECT *FROM menu")
    menus = cur.fetchall()

    if result > 0:
        return render_template('dashboard1.html',menus=menus)
    else:
        msg = 'No Entry'
        return render_template('dashboard1.html',msg=msg)
    cur.close()

@app.route('/room_status', methods = ['GET', 'POST'])
@is_logged_in
def room():
   
        #student_reciept=session['student_recepit']
        
        total_rooms=20
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT *FROM room")
      
        if result==0:
            lst=[]
            lst1=[]
            for i in range(1,21):
                lst.append(i)
            lst1=sorted(lst)
            for i in lst1:
                cur.execute("INSERT INTO room(room_no) VALUES(%s)",[i])
        rooms=cur.fetchall()
        mysql.connection.commit()

        cur.close()
    
        #return redirect(url_for('room_status'))
        return render_template('room_status.html',rooms=rooms)
    
@app.route('/change_roomstatus1/<string:room_no>',methods=['GET','POST'])
@is_logged_in
def change_roomstatus1(room_no):
    cur=mysql.connection.cursor()
    cur.execute("UPDATE room SET student1 =1 WHERE room_no=%s",[room_no])
    mysql.connection.commit()

    cur.close()
    #flash('','success')

    return redirect(url_for('room'))


@app.route('/change_roomstatus2/<string:room_no>',methods=['GET','POST'])
@is_logged_in
def change_roomstatus2(room_no):
    cur=mysql.connection.cursor()
    cur.execute("UPDATE room SET student2 =1 WHERE room_no=%s",[room_no])
    mysql.connection.commit()

    cur.close()
    #flash('','success')

    return redirect(url_for('room'))

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(host='0.0.0.0',debug=True)
    
