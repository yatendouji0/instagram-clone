import os
from flask import Flask, flash, render_template, redirect, request, session, url_for
import sqlite3
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'ereninstasecret'


db = sqlite3.connect(os.getcwd().replace('\\','/')+'/app/db.db', check_same_thread=False)
db.row_factory = sqlite3.Row

#Tolist
def tolist(list_):
    list__ = list()
    for i in list_:
        list__.append(i[0])
    return list__


# Login required decorator
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'loggedin' in session:
            return func(*args, **kwargs)
        return redirect(url_for('login'))
    return wrapper

# Following detection
def follow_detection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cur = db.cursor()
        query = 'SELECT * FROM following WHERE who = "{}" and whom = "{}"'
        cur.execute(query.format(session['username'],kwargs['username']))
        data = cur.fetchone()
        cur.close()
        if data == None:
            return func(*args,**kwargs)
        return redirect(url_for('profile',username=kwargs['username']))
    return wrapper

#index page
@app.route('/')
@login_required
def index():
    if not 'pp' in session:
        cur = db.cursor()
        query = 'SELECT pp FROM users WHERE username = "{}"'
        cur.execute(query.format(session['username']))
        data = cur.fetchone()
        cur.close()
        session['pp'] = data['pp']

    cur = db.cursor()
    query = 'SELECT whom FROM following WHERE who = "{}"'.format(session['username'])
    cur.execute(query)
    following = cur.fetchall()
    followList = list()
    for i in following:
        followList.append(i['whom'])
    if len(followList) == 1: query = 'SELECT * FROM posts WHERE whose = "{}"'.format(followList[0])
    else: query = 'SELECT * FROM posts WHERE whose IN {} ORDER BY id DESC'.format(tuple(followList))
    cur.execute(query)
    postdata = cur.fetchall()
    cur.close()

    return render_template('index.html',postdata = postdata) 

#Login and Signup
@app.route('/login', methods=('GET','POST'))
def login():
    if request.method == 'POST':
        noe = request.form['noe']
        password = request.form['password']

        cur = db.cursor()
        query = 'SELECT * FROM users WHERE username = "{}" or email = "{}"'
        cur.execute(query.format(noe,noe))
        data = cur.fetchall()
        cur.close()

        if(len(data) == 0):
            flash('Böyle bir kullanıcı adı bulunmuyor.','danger')
            return redirect('login')

        for i in data:
            if (i['username'] == noe or i['email'] == noe) and sha256_crypt.verify(password,i['password']):
                session['loggedin'] = True
                session['username'] = i['username']
                session['pp'] = i['pp']
                return redirect(url_for('index'))
        
        flash('Şifreniz hatalı','danger')
        return redirect('login')

    return render_template('login.html', navbar = False)

@app.route('/signup', methods=('GET','POST'))
def signup():
    if request.method == 'POST':
        email = request.form['email']
        fullname = request.form['name']
        username = request.form['username']
        password = request.form['password']
        password = sha256_crypt.encrypt(password)

        cur = db.cursor()
        query = 'INSERT INTO users(email,fullname,username,password,pp) VALUES("{}","{}","{}","{}","{}")'
        cur.execute(query.format(email,fullname,username,password,'0.png'))
        db.commit()
        cur.close()

        flash('Başarıyla kayıt oldunuz.','success')
        return redirect(url_for('login'))

    return render_template('signup.html',navbar = False)

# Logout
@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

# Profile / Users
@app.route('/<string:username>')
def profile(username):
    
    cur = db.cursor()
    query = 'SELECT * FROM users WHERE username = "{}"'
    cur.execute(query.format(username))
    userdata = dict(cur.fetchone())
    follower = cur.execute('SELECT COUNT(who) FROM following WHERE whom = "{}"'.format(username)).fetchone()['COUNT(who)']
    following = cur.execute('SELECT COUNT(whom) FROM following WHERE who = "{}"'.format(username)).fetchone()['COUNT(whom)']
    followingbyme = cur.execute('SELECT COUNT(whom) FROM following WHERE who = "{}" and whom = "{}"'.format(session['username'],username)).fetchone()['COUNT(whom)']
    followdata = {
        'follower': follower,
        'following': following,
        'followingbyme': followingbyme
    }
    query = 'SELECT id,postimg FROM posts WHERE whose = "{}"'
    cur.execute(query.format(username))
    postdata = cur.fetchall()
    cur.close()
    session['followdata'] = followdata
    session['userdata'] = userdata
    return render_template('profile.html', userdata = userdata, followdata=followdata, postdata = postdata)

# Follow
@app.route('/follow/<string:username>')
@login_required
@follow_detection
def follow(username):

    cur = db.cursor()
    query = 'INSERT INTO following VALUES("{}","{}")'
    cur.execute(query.format(session['username'],username))
    db.commit()
    cur.close()

    return redirect(url_for('profile', username=username))

@app.route('/unfollow/<string:username>')
@login_required
def unfollow(username):

    cur = db.cursor()
    query = 'DELETE FROM following WHERE who = "{}" and whom = "{}"'
    cur.execute(query.format(session['username'],username))
    db.commit()
    cur.close()

    return redirect(url_for('profile',username=username))

@app.route('/<string:username>/followers')
def followers(username):

    cur = db.cursor()
    query = 'SELECT who FROM following WHERE whom = "{}"'
    cur.execute(query.format(username))
    followers = cur.fetchall()
    followers = tolist(followers)
    if len(followers) == 1:
        query = 'SELECT * FROM users WHERE username IN ("{}")'
        cur.execute(query.format(followers[0]))
    else: 
        query = 'SELECT * FROM users WHERE username IN {}'
        cur.execute(query.format(tuple(i for i in followers)))
    
    followers = cur.fetchall()
    cur.close()
    return render_template('follow_page.html', userdata=session['userdata'], followdata=session['followdata'], followers = followers, lenfollow = len(followers),title="Takipçiler")

@app.route('/<string:username>/following')
def following(username):

    cur = db.cursor()
    query = 'SELECT whom FROM following WHERE who = "{}"'
    cur.execute(query.format(username))
    following = cur.fetchall()
    following = tolist(following)
    if len(following) == 1:
        query = 'SELECT * FROM users WHERE username IN ("{}")'
        cur.execute(query.format(following[0]))
    else: 
        query = 'SELECT * FROM users WHERE username IN {}'
        cur.execute(query.format(tuple(i for i in following)))
    
    following = cur.fetchall()
    cur.close()
    return render_template('follow_page.html', userdata=session['userdata'], followdata=session['followdata'], followers = following, lenfollow = len(following), title="Takip Ettikleri")

# Searching
@app.route('/search', methods=('POST','GET'))
def search():
    if request.method == 'POST':
        search = request.form['search']
        cur = db.cursor()
        query = 'SELECT * FROM users WHERE username LIKE "%{}%" '
        cur.execute(query.format(search))
        data = cur.fetchall()
        cur.close()
        print(data)
        return render_template('search.html', searchTitle=search, userdatas = data)
    return redirect('index')

# Post Upload
@app.route('/posts/upload', methods=('POST','GET'))
@login_required
def postupload():
    if request.method == 'POST':
        postimg = request.files['postimg']
        posttext = request.form['posttext']
        posttext = '' if posttext == None else posttext
        extensions = ('.png','.jpg','.jpeg')
        if not postimg.filename.endswith(extensions):
            flash('Bu dosya uzantısı desteklenmiyor.','danger')
            return redirect(url_for('postupload'))

        cur = db.cursor()
        postcount = cur.execute('SELECT COUNT(*) FROM posts WHERE whose = "{}"'.format(session['username'])).fetchone()[0]
        postimg.filename = secure_filename(session['username']+'_post_'+str(postcount)+'_'+postimg.filename)

        query = 'INSERT INTO posts(whose,whosepp,postimg,posttext) VALUES("{}","{}","{}","{}")'
        cur.execute(query.format(session['username'], session['pp'], postimg.filename, posttext))
        db.commit()
        cur.close()
        postimg.save(os.getcwd().replace('\\','/') + '/static/postimg/' + postimg.filename)
        flash('Gönderiniz başarıyla yüklendi.','success')
        return redirect(url_for('profile', username=session['username']))

    return render_template('uploadpost.html')

#Post Delete
@app.route('/posts/delete/<int:id>')
@login_required
def delpost(id):
    
    cur = db.cursor()
    query = 'SELECT whose FROM posts WHERE id = {}'.format(id)
    cur.execute(query)
    data = cur.fetchone()
    if data['whose'] == session['username']:
        query = 'DELETE FROM posts WHERE id = {}'.format(id)
        cur.execute(query)
        db.commit()
    else:
        return redirect(url_for('index'))
    cur.close()
    flash('1 gönderiyi sildiniz.','warning')
    return redirect(url_for('index'))

#Post Page
@app.route('/posts/<int:id>')
def postview(id):

    cur = db.cursor()
    query = 'SELECT * FROM posts WHERE id = {}'
    cur.execute(query.format(id))
    data = cur.fetchone()
    query = 'SELECT * FROM users WHERE username = "{}"'
    cur.execute(query.format(data['whose']))
    userdata = cur.fetchone()
    query = 'SELECT * FROM comment WHERE for={}'
    cur.execute(query.format(id))
    comments = cur.fetchall()
    cur.close()
    comments = None if len(comments) == 0 else comments
    if data == None: return redirect('index') 
    return render_template('postpage.html',post = data, user = userdata, comments = comments)

#Add Comment
@app.route('/posts/<int:id>/addcomment', methods=('POST',))
@login_required
def addcomment(id):
    comment = request.form['comment']
    cur = db.cursor()
    query = 'INSERT INTO comment VALUES({},"{}","{}","{}")'
    cur.execute(query.format(id,session['username'],session['pp'],comment))
    db.commit()
    cur.close()
    return redirect(url_for('postview', id=id))

#----------------------------------------