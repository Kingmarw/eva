import os
import cloudinary
import cloudinary.uploader
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL is not set!")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace("postgres://", "postgresql://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'supersecretkey'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
# ✅ إعداد Cloudinary
cloudinary.config(
    cloud_name="djlyxjsnv",
    api_key="129551634188336",
    api_secret="9p2ld51tdCgPzBajwAtrA575gFc"
)

# ✅ تعريف نموذج المستخدم
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    profile_pic = db.Column(db.String(500), nullable=True)  # رابط صورة الملف الشخصي
    cover_pic = db.Column(db.String(500), nullable=True)    # رابط صورة الغلاف
    role = db.Column(db.String(50), default="user")  # 🟢 الدور: "user" أو "admin"

# ✅ نموذج التقييمات
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    review_link = db.Column(db.String(500), nullable=False)
    review_name = db.Column(db.String(255), nullable=False)
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

class Homework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    homework_name = db.Column(db.String(255), nullable=False)  # اسم الواجب
    subject = db.Column(db.String(100), nullable=False)  # المادة
    homework_link = db.Column(db.String(500), nullable=False)  # رابط الواجب
    user = db.relationship('User', backref=db.backref('homeworks', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@login_required
def home():
    return render_template("index.html", username=current_user.username, profile_pic=current_user.profile_pic)

# ✅ تسجيل مستخدم جديد مع رفع الصور
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        # ✅ تعيين المشرف تلقائيًا لو كان الاسم والباسورد محددين
        if username == "admin" and password == "adminpassword123@":
            role = "admin"
        else:
            role = "user"
        
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        profile_pic = request.files.get("profile_pic")
        cover_pic = request.files.get("cover_pic")

        # ✅ رفع الصور لـ Cloudinary
        profile_pic_url = None
        cover_pic_url = None

        if profile_pic and profile_pic.filename != '':
            result = cloudinary.uploader.upload(profile_pic)
            profile_pic_url = result["secure_url"]

        if cover_pic and cover_pic.filename != '':
            result = cloudinary.uploader.upload(cover_pic)
            cover_pic_url = result["secure_url"]

        # ✅ حفظ المستخدم في قاعدة البيانات
        new_user = User(username=username, password=hashed_password, role=role, profile_pic=profile_pic_url, cover_pic=cover_pic_url)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# ✅ رفع التقييمات
@app.route("/upload_eva", methods=["GET", "POST"])
@login_required
def upload_review():
    if request.method == "POST":
        review_name = request.form.get("review_name")
        review_link = request.form.get("review_link")
        subject = request.form.get("subject")  # ✅ جلب المادة من الفورم

        # ✅ تحقق من القيم المدخلة قبل إضافة التقييم
        if not review_name or not review_link or not subject:
            flash("يجب ملء جميع الحقول!", "danger")
            return redirect(url_for("upload_review"))

        # ✅ إنشاء التقييم وإضافته إلى قاعدة البيانات
        new_review = Review(user_id=current_user.id, review_name=review_name, review_link=review_link, subject=subject)
        db.session.add(new_review)
        db.session.commit()
        
        flash("تم رفع التقييم بنجاح!", "success")
        return redirect(url_for("view_reviews"))

    return render_template("upload_eva.html", username=current_user.username, profile_pic=current_user.profile_pic)


@app.route("/delete_review/<int:review_id>", methods=["POST"])
@login_required
def delete_review(review_id):
    if current_user.role != "admin":
        return "غير مصرح لك بحذف التقييمات", 403

    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    return redirect(url_for("view_reviews"))


# ✅ عرض التقييمات
@app.route("/eva")
@login_required
def view_reviews():
    reviews = Review.query.all()

    # تجميع التقييمات حسب المادة
    grouped_reviews = {}
    for review in reviews:
        if review.subject not in grouped_reviews:
            grouped_reviews[review.subject] = []
        grouped_reviews[review.subject].append(review)

    return render_template("eva.html", grouped_reviews=grouped_reviews, username=current_user.username, profile_pic=current_user.profile_pic)


@app.route("/upload_homework", methods=["GET", "POST"])
@login_required
def upload_homework():
    if request.method == "POST":
        homework_name = request.form.get("homework_name")
        subject = request.form.get("subject")
        homework_link = request.form.get("homework_link")

        if not homework_name or not subject or not homework_link:
            flash("يجب ملء جميع الحقول!", "danger")
            return redirect(url_for("upload_homework"))

        new_homework = Homework(user_id=current_user.id, homework_name=homework_name, subject=subject, homework_link=homework_link)
        db.session.add(new_homework)
        db.session.commit()
        
        flash("تم رفع الواجب بنجاح!", "success")
        return redirect(url_for("view_homeworks"))

    return render_template("upload_homework.html",username=current_user.username, profile_pic=current_user.profile_pic)


@app.route("/homeworks")
@login_required
def view_homeworks():
    homeworks = Homework.query.all()
    grouped_homeworks = {}

    for homework in homeworks:
        if homework.subject not in grouped_homeworks:
            grouped_homeworks[homework.subject] = []
        grouped_homeworks[homework.subject].append(homework)

    return render_template("homeworks.html", grouped_homeworks=grouped_homeworks,username=current_user.username, profile_pic=current_user.profile_pic)



@app.route("/delete_homework/<int:homework_id>", methods=["POST"])
@login_required
def delete_homework(homework_id):
    if current_user.role != "admin":
        flash("غير مسموح لك بحذف الواجبات!", "danger")
        return redirect(url_for("view_homeworks"))

    homework = Homework.query.get_or_404(homework_id)
    db.session.delete(homework)
    db.session.commit()
    
    flash("تم حذف الواجب بنجاح!", "success")
    return redirect(url_for("view_homeworks"))

# ✅ صفحة تسجيل الدخول
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("home"))
    return render_template("login.html")

# ✅ صفحة الملف الشخصي
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", username=current_user.username, profile_pic=current_user.profile_pic, cover_pic=current_user.cover_pic)

# ✅ تسجيل الخروج
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ✅ تشغيل التطبيق وإنشاء قاعدة البيانات
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
