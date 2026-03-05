from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tasks = db.relationship('Todo', backref='owner', lazy=True)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Work / Personal
    due_date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = generate_password_hash(request.form.get('password'))

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("User already exists!", "error")
            return redirect(url_for('register'))   # stays on register page

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))  # go to login page

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('index'))  # show on index page
        else:
            flash("Invalid credentials!", "error")
            return redirect(url_for('login'))  # show on login page

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# @app.route('/')
# @login_required
# def index():
#     tasks = Todo.query.filter_by(user_id=current_user.id).all()
#     return render_template('index.html', tasks=tasks)

from datetime import date
from flask_login import login_required, current_user

# @app.route('/')
# @login_required
# def index():

#     tasks = Todo.query.filter_by(user_id=current_user.id).all()
#     # Dashboard counts
#     total_tasks = Todo.query.filter_by(user_id=current_user.id).count()
#     completed_tasks = Todo.query.filter_by(
#         user_id=current_user.id,
#         completed=True
#     ).count()
#     pending_tasks = Todo.query.filter_by(
#         user_id=current_user.id,
#         completed=False
#     ).count()
#     overdue_tasks = Todo.query.filter(
#         Todo.user_id == current_user.id,
#         Todo.completed == False,
#         Todo.due_date < date.today()
#     ).count()
#     return render_template(
#         'index.html',
#         tasks=tasks,
#         total_tasks=total_tasks,
#         completed_tasks=completed_tasks,
#         pending_tasks=pending_tasks,
#         overdue_tasks=overdue_tasks
#     )


@app.route('/')
@login_required
def index():

    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    status = request.args.get('status')
    search = request.args.get('search')

    query = Todo.query.filter_by(user_id=current_user.id)

    # Filter by category
    if category and category != "All":
        query = query.filter(Todo.category == category)

    # Filter by status
    if status == "Completed":
        query = query.filter(Todo.completed == True)
    elif status == "Pending":
        query = query.filter(Todo.completed == False)

    # Search by title
    if search:
        query = query.filter(Todo.title.ilike(f"%{search}%"))

    # Pagination (5 per page)
    pagination = query.order_by(Todo.id.desc()).paginate(
        page=page,
        per_page=5
    )

    tasks = pagination.items

    # 📊 Dashboard counts (without filters — overall stats)
    total_tasks = Todo.query.filter_by(user_id=current_user.id).count()
    completed_tasks = Todo.query.filter_by(user_id=current_user.id, completed=True).count()
    pending_tasks = Todo.query.filter_by(user_id=current_user.id, completed=False).count()

    today = date.today()
    overdue_count = 0

    for task in tasks:
        if task.due_date and task.due_date < today and task.completed != "Completed":
            overdue_count += 1

    # overdue_count = len(overdue_tasks)

    return render_template(
        'index.html',
        tasks=tasks,
        pagination=pagination,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        overdue_count=overdue_count
    )

# @app.route('/add', methods=['POST'])
# @login_required
# def add():
#     title = request.form.get('title')
#     category = request.form.get('category')
#     due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()

#     new_task = Todo(
#         title=title,
#         category=category,
#         due_date=due_date,
#         user_id=current_user.id
#     )

#     db.session.add(new_task)
#     db.session.commit()

#     flash("Task Added Successfully!")
#     return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_task():

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        due_date_str = request.form.get('due_date')

        due_date = None
        if due_date_str:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()

        new_task = Todo(
            title=title,
            category=category,
            due_date=due_date,
            user_id=current_user.id
        )

        db.session.add(new_task)
        db.session.commit()

        flash("Task Added Successfully!", "success")
        return redirect(url_for('index'))

    return render_template('add_task.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    task = Todo.query.get_or_404(id)

    if task.user_id != current_user.id:
        flash("Unauthorized access!")
        return redirect(url_for('index'))

    if request.method == 'POST':
        task.title = request.form.get('title')
        task.category = request.form.get('category')
        task.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        task.completed = 'completed' in request.form

        db.session.commit()
        flash("Task Updated Successfully!")
        return redirect(url_for('index'))

    return render_template('edit.html', task=task)


@app.route('/delete/<int:id>')
@login_required
def delete(id):
    task = Todo.query.get_or_404(id)

    if task.user_id != current_user.id:
        flash("Unauthorized access!")
        return redirect(url_for('index'))

    db.session.delete(task)
    db.session.commit()

    flash("Task Deleted Successfully!")
    return redirect(url_for('index'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run()
