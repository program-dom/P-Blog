from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, NewUserForm, LogIn, CommentForm, ContactForm
from flask_gravatar import Gravatar
from functools import wraps
from flask import abort
import smtplib
import os
from dotenv import load_dotenv
from pathlib import Path

# loading and reading env var
envars = Path('information.env')
load_dotenv(dotenv_path=envars)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_BINDS'] = {'users': 'sqlite:///users.db', 'comments': 'sqlite:///comments.db'}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


#CONFIGURE TABLES

class User(UserMixin, db.Model):
    # PARENT TABLE
    # using bind key to bind the table to the main db
    __bind_key__ = "users"
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(50))

    children = relationship("BlogPost", back_populates="parent")
    comments = relationship("Comments", back_populates="commenter")
# db.create_all()


class BlogPost(db.Model):
    # CHILD TABLE
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # CONNECTING DB WITH USERS
    # "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent = relationship("User", back_populates="children")

    # CONNECTING DB WITH COMMENTS
    comments = relationship("Comments", back_populates="posts")
# db.create_all()


class Comments(db.Model):
    __bind_key__ = "comments"
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # CONNECTING DB WITH USERS
    commenter_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    commenter = relationship("User", back_populates="comments")

    # CONNECTING DB WITH BLOG POSTS
    blog_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    posts = relationship("BlogPost", back_populates="comments")
db.create_all()

# GRAVATAR INITIALIZING
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False,
                    force_lower=False, use_ssl=False, base_url=None)


login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


@app.route('/register', methods=["POST", "GET"])
def register():
    new_user = NewUserForm()
    if new_user.validate_on_submit():
        if User.query.filter_by(email=new_user.email.data).first():
            flash("User already exists. Try logging in.")
            return redirect(url_for('login'))

        hash_pass = generate_password_hash(new_user.password.data, method='pbkdf2:sha256', salt_length=8)
        user = User(
            email=new_user.email.data,
            password=hash_pass,
            name=new_user.name.data
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=new_user)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LogIn()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Incorrect password entered.Please try again.")
                return redirect(url_for('login'))
        else:
            flash("User does not exist. Please try again.")
            return redirect(url_for('login'))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for('login'))

        new_comment = Comments(
            text=form.comment.data,
            commenter=current_user,
            posts=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=requested_post.id))
    return render_template("post.html", post=requested_post, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


my_mail = os.environ.get('MY_MAIL')
password = os.environ.get('PASSWORD')


@app.route("/contact", methods=["POST", "GET"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        with smtplib.SMTP("smtp.gmail.com") as connect:
            connect.starttls()
            connect.login(user=my_mail, password=password)
            connect.sendmail(
                from_addr=my_mail,
                to_addrs="dpoulomi58@yahoo.com",
                msg=f"Subject:Website Mail\n\n Name:{form.name.data}\n"
                    f"Email:{form.email.data}\n"
                    f"Phone No:{form.phone.data}\n"
                    f"Message:{form.message.data}"
            )
        flash("Successfully sent your message!")
        return redirect(url_for('contact'))
    else:
        return render_template("contact.html", form=form)


@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/delete-comment/<int:comment_id>/<int:post_id>")
@login_required
def delete_comment(comment_id, post_id):
    comment_to_delete = Comments.query.get(comment_id)
    post = BlogPost.query.get(post_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post.id))


if __name__ == "__main__":
    app.run(debug=True)
