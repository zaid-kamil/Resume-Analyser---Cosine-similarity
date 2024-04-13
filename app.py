from flask import Flask, render_template,redirect,request, flash, session
from database import User, add_to_db, open_db, File, open_db, Job
from werkzeug.utils import secure_filename
import os
from doctotext import extract_text_from_docx
from pdf2text import extract_text_from_pdf
from entity_recognizer import extract_skills, extract_names, extract_emails
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'thisissupersecretkeyfornoone'

app.config['UPLOAD_PATH'] = 'static/uploads'

@app.route('/')
def index():
    # check login
    if not session.get('isauth'):
        return redirect('/login')
    if session.get('isadmin'):
        jobs = open_db().query(Job).all()
        resumes = open_db().query(File).all()
        return render_template('index.html', jobs=jobs, resumes=resumes)
    else:
        resumes = open_db().query(File).filter(File.user_id==session.get('id', 1)).all()
        return render_template('index.html', resumes=resumes)
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        print("Email =>", email)
        print("Password =>", password)
        if email and password:
            db = open_db()
            user = db.query(User).filter(User.email==email).first()
            if user is not None and user.password == password:
                session['isauth'] = True
                session['id'] = user.id
                session['email'] = user.email
                session['username'] = user.username
                if user.username == 'admin':
                    session['isadmin'] = True
                flash('You are logged In', 'success')
                
                return redirect('/')
            else:
                flash('credentials do not match', 'danger')
        else:
            flash('email and password cant be empty','danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if session.get('isauth'):   
        session.clear()
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        cpassword = request.form.get('cpassword')
        print(username, email, password, cpassword)
        # logic
        if len(username) == 0 or len(email) == 0 or len(password) == 0 or len(cpassword) == 0:
            flash("All fields are required", 'danger')
            return redirect('/register') # reload the page
        user = User(username=username, email=email, password=password)
        add_to_db(user)
    return render_template('register.html')

@app.route('/resume/add', methods=['GET', 'POST'])
def resumeadd():
    if request.method == 'POST':
        filetype = request.form.get('formtype')
        if filetype == 'pdf':
            pdffile = request.files.get('pdffile')
            filename = secure_filename(pdffile.filename)
            if filename != '':
                if not os.path.exists(app.config['UPLOAD_PATH']):
                    os.makedirs(app.config['UPLOAD_PATH'])
                path = os.path.join(app.config['UPLOAD_PATH'],filename)     # make os compatible path string
                try:
                    pdffile.save(path)
                    add_to_db(File(path=path, user_id=session.get('id', 1)))
                    flash('File uploaded', 'success')
                    return redirect('/resume/add')
                except Exception as e:
                    print(e)
                    flash('File not uploaded', 'danger')
                    return redirect('/resume/add')
            else:
                flash('filename is empty')
                print('filename is empty')
    # load all saved resumes from the user
    db = open_db()
    files = db.query(File).filter(File.user_id==session.get('id', 1)).all()
    return render_template('addresume.html', resumes=files)

# delete resume
@app.route('/resume/delete/<int:id>')
def resumedelete(id):
    db = open_db()
    file = db.query(File).filter(File.id==id).first()
    if file is not None:
        try:
            os.remove(file.path)
            db.delete(file)
            db.commit()
            flash('File deleted', 'success')
        except Exception as e:
            print(e)
            flash('File not deleted', 'danger')
    return redirect('/resume/add')

# view resume
@app.route('/resume/view/<int:id>')
def resumeview(id):
    db = open_db()
    file = db.query(File).filter(File.id==id).first()
    if file is not None:
        return render_template('viewresume.html', file=file)
    return redirect('/resume/add')

# edit resume
@app.route('/job/add', methods=['GET', 'POST'])
def jobadd():
    if request.method == 'POST':
        jobTitle = request.form.get('jobTitle')
        jobDescription= request.form.get('jobDescription')
        jobLocation = request.form.get('jobLocation')
        jobType = request.form.get('jobType')
        print("jobTitle =>", jobTitle)
        print("jobDescription =>", jobDescription)
        print("jobLocation  =>", jobLocation )
        print("jobType =>", jobType)
        # logic
        if len(jobTitle) == 0 or len(jobDescription) == 0 or len(jobLocation) == 0 or len(jobType) == 0:
            flash("All fields are required", 'danger')
            return redirect('/register') # reload the page
        job = Job(job_title=jobTitle, job_description=jobDescription, job_location=jobLocation, job_type=jobType)
        add_to_db(job)
        flash('job aded', 'success')
        return redirect('/job/list')
    return render_template('addjob.html')

@app.route('/job/list')
def job_list():
    db = open_db()
    jobs = db.query(Job).all()
    return render_template('joblist.html', jobs=jobs)

# delete job
@app.route('/job/delete/<int:id>')
def jobdelete(id):
    db = open_db()
    job = db.query(Job).filter(Job.id==id).first()
    if job is not None:
        try:
            db.delete(job)
            db.commit()
            flash('Job deleted', 'success')
        except Exception as e:
            print(e)
            flash('Job not deleted', 'danger')
    return redirect('/job/list')

# view job
@app.route('/job/view/<int:id>')
def jobview(id):
    db = open_db()
    job = db.query(Job).filter(Job.id==id).first()
    if job is not None:
        return render_template('viewjob.html', job=job)
    return redirect('/job/list')

# match job
@app.route('/job/match/<int:id>', methods=['GET', 'POST'])
def jobmatch(id):
    db = open_db()
    job = db.query(Job).filter(Job.id==id).first()
    if job is not None:
        resumes = db.query(File).all()
        results = []
        for resume in resumes:
            if resume.path.endswith('.docx'):
                resume_text = extract_text_from_docx(resume.path)
            else:
                resume_text = extract_text_from_pdf(resume.path)

            name = extract_names(resume_text)
            email = extract_emails(resume_text)
            data = [resume_text, job.job_description]
            cv = CountVectorizer()    
            count_matrix = cv.fit_transform(data)
            matchPercentage = round(cosine_similarity(count_matrix)[0][1] * 100,2)
            results.append({
                'resume': resume,
                'keywords': list(set(name)),
                'email': email[0],
                'score': matchPercentage
            })
        flash("Successfully analyzed the resumes", "success")
        return render_template('matchjob.html', job=job, results=results)            
    return redirect('/job/list')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
 

 