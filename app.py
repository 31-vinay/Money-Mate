from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from models import db, User, Income, Expense, Goal
from forms import (
    RegistrationForm,
    LoginForm,
    IncomeForm,
    ExpenseForm,
    GoalForm,
    SavingsUpdateForm,
)
from datetime import datetime, timedelta
from sqlalchemy import func
from collections import defaultdict
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import os

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

admin = Admin(app, name="Finance Manager")
app.config["SECRET_KEY"] = os.environ.get("SESSION_SECRET", "your-secret-key-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Add admin panel


# Protect admin views with login
class AdminModelView(ModelView):
    def is_accessible(self):
        return (
            current_user.is_authenticated and current_user.username == "admin"
        )  # Change to your admin username

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login"))


# Add your models to admin
admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Income, db.session))
admin.add_view(AdminModelView(Expense, db.session))
admin.add_view(AdminModelView(Goal, db.session))


@app.route("/create_admin")
def create_admin():
    # Check if admin already exists
    admin_user = User.query.filter_by(username="admin").first()
    if not admin_user:
        admin_user = User(
            username="admin", email="admin@example.com", password="admin123"
        )
        db.session.add(admin_user)
        db.session.commit()
        return "Admin user created! Username: admin, Password: admin123"
    return "Admin user already exists"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create tables and run any needed column migrations
with app.app_context():
    db.create_all()
    # Add has_seen_tutorial column for existing databases
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE user ADD COLUMN has_seen_tutorial BOOLEAN DEFAULT 0 NOT NULL"))
            conn.commit()
    except Exception:
        pass  # Column already exists

# Category hierarchy from ChatGPT
expense_categories = {
    "Housing": {
        "subcategories": [
            "Rent",
            "Mortgage",
            "Property Tax",
            "Home Maintenance",
            "Home Repairs",
            "Furniture",
            "Home Decor",
            "Security System",
            "Cleaning Services",
            "Home Insurance",
        ],
        "classification": {
            "Rent": "need",
            "Mortgage": "need",
            "Property Tax": "need",
            "Home Maintenance": "need",
            "Home Repairs": "need",
            "Furniture": "want",
            "Home Decor": "want",
            "Security System": "need",
            "Cleaning Services": "want",
            "Home Insurance": "need",
        },
    },
    "Food & Groceries": {
        "subcategories": [
            "Groceries",
            "Basic Food Staples",
            "Dining Out",
            "Fast Food",
            "Coffee Shops",
            "Food Delivery",
            "Snacks",
            "Meal Kits",
            "Specialty Foods",
        ],
        "classification": {
            "Groceries": "need",
            "Basic Food Staples": "need",
            "Dining Out": "want",
            "Fast Food": "want",
            "Coffee Shops": "want",
            "Food Delivery": "want",
            "Snacks": "want",
            "Meal Kits": "want",
            "Specialty Foods": "want",
        },
    },
    "Transportation": {
        "subcategories": [
            "Fuel",
            "Public Transport",
            "Taxi/Rideshare",
            "Vehicle Maintenance",
            "Vehicle Insurance",
            "Parking Fees",
            "Tolls",
            "Car Loan Payment",
            "Car Wash",
            "Vehicle Registration",
        ],
        "classification": {
            "Fuel": "need",
            "Public Transport": "need",
            "Taxi/Rideshare": "want",
            "Vehicle Maintenance": "need",
            "Vehicle Insurance": "need",
            "Parking Fees": "need",
            "Tolls": "need",
            "Car Loan Payment": "need",
            "Car Wash": "want",
            "Vehicle Registration": "need",
        },
    },
    "Utilities": {
        "subcategories": [
            "Electricity",
            "Water",
            "Gas",
            "Internet",
            "Mobile Phone",
            "Trash Collection",
            "Sewer Charges",
            "Streaming Bundled with Internet",
        ],
        "classification": {
            "Electricity": "need",
            "Water": "need",
            "Gas": "need",
            "Internet": "need",
            "Mobile Phone": "need",
            "Trash Collection": "need",
            "Sewer Charges": "need",
            "Streaming Bundled with Internet": "want",
        },
    },
    "Healthcare": {
        "subcategories": [
            "Doctor Visits",
            "Hospital Bills",
            "Pharmacy",
            "Health Insurance",
            "Dental Care",
            "Vision Care",
            "Mental Health Therapy",
            "Medical Equipment",
            "Health Supplements",
        ],
        "classification": {
            "Doctor Visits": "need",
            "Hospital Bills": "need",
            "Pharmacy": "need",
            "Health Insurance": "need",
            "Dental Care": "need",
            "Vision Care": "need",
            "Mental Health Therapy": "need",
            "Medical Equipment": "need",
            "Health Supplements": "want",
        },
    },
    "Education": {
        "subcategories": [
            "School Tuition",
            "College Tuition",
            "Online Courses",
            "Books",
            "School Supplies",
            "Professional Certifications",
            "Workshops",
            "Educational Software",
        ],
        "classification": {
            "School Tuition": "need",
            "College Tuition": "need",
            "Online Courses": "want",
            "Books": "need",
            "School Supplies": "need",
            "Professional Certifications": "need",
            "Workshops": "want",
            "Educational Software": "need",
        },
    },
    "Insurance": {
        "subcategories": [
            "Health Insurance",
            "Life Insurance",
            "Vehicle Insurance",
            "Home Insurance",
            "Travel Insurance",
            "Pet Insurance",
        ],
        "classification": {
            "Health Insurance": "need",
            "Life Insurance": "need",
            "Vehicle Insurance": "need",
            "Home Insurance": "need",
            "Travel Insurance": "want",
            "Pet Insurance": "want",
        },
    },
    "Personal & Lifestyle": {
        "subcategories": [
            "Clothing",
            "Shoes",
            "Haircuts",
            "Beauty Products",
            "Gym Membership",
            "Salon Services",
            "Spa",
            "Personal Care Items",
        ],
        "classification": {
            "Clothing": "need",
            "Shoes": "need",
            "Haircuts": "need",
            "Beauty Products": "want",
            "Gym Membership": "want",
            "Salon Services": "want",
            "Spa": "want",
            "Personal Care Items": "need",
        },
    },
    "Entertainment": {
        "subcategories": [
            "Movies",
            "Concerts",
            "Gaming",
            "Streaming Subscriptions",
            "Hobbies",
            "Books & Magazines",
            "Theme Parks",
            "Events & Shows",
        ],
        "classification": {
            "Movies": "want",
            "Concerts": "want",
            "Gaming": "want",
            "Streaming Subscriptions": "want",
            "Hobbies": "want",
            "Books & Magazines": "want",
            "Theme Parks": "want",
            "Events & Shows": "want",
        },
    },
    "Travel": {
        "subcategories": [
            "Flights",
            "Hotels",
            "Vacation Packages",
            "Local Travel",
            "Travel Insurance",
            "Tour Guides",
            "Resort Stay",
        ],
        "classification": {
            "Flights": "want",
            "Hotels": "want",
            "Vacation Packages": "want",
            "Local Travel": "need",
            "Travel Insurance": "want",
            "Tour Guides": "want",
            "Resort Stay": "want",
        },
    },
    "Debt & Financial Obligations": {
        "subcategories": [
            "Credit Card Payment",
            "Loan Repayment",
            "Student Loan Payment",
            "Personal Loan",
            "Bank Fees",
            "Late Fees",
        ],
        "classification": {
            "Credit Card Payment": "need",
            "Loan Repayment": "need",
            "Student Loan Payment": "need",
            "Personal Loan": "need",
            "Bank Fees": "need",
            "Late Fees": "want",
        },
    },
    "Other": {
        "subcategories": ["Other (User Input)"],
        "classification": {"Other (User Input)": "unknown"},
    },
}

# Flatten the needs keywords for backward compatibility
essential_keywords = []
for main_cat, data in expense_categories.items():
    classification_map = data.get("classification", {})
    if isinstance(classification_map, dict):
        for subcat, classification in classification_map.items():
            if classification == "need":
                essential_keywords.append(subcat.lower())
                if main_cat.lower() not in essential_keywords:
                    essential_keywords.append(main_cat.lower())


def classify_essential(main_category, sub_category, custom_category=None):
    if sub_category is None:
        return False

    if sub_category == "Other (User Input)" and custom_category:
        return classify_essential_keywords(custom_category)

    if main_category and main_category in expense_categories:
        cat_data = expense_categories[main_category]
        if sub_category in cat_data["classification"]:
            classification = cat_data["classification"][sub_category]
            if classification == "need":
                return True
            elif classification == "want":
                return False

    return classify_essential_keywords(sub_category)


def classify_essential_keywords(text):
    if text is None or text == "":
        return False
    text_lower = text.lower()
    for kw in essential_keywords:
        if kw in text_lower:
            return True
    return False


# Helper: detect recurring subscriptions
def detect_subscriptions(user_id, months_back=3):
    since_date = datetime.utcnow() - timedelta(days=30 * months_back)
    expenses = Expense.query.filter(
        Expense.user_id == user_id, Expense.date >= since_date
    ).all()

    groups = defaultdict(list)
    for exp in expenses:
        key = (
            exp.category.strip().lower(),
            exp.description.strip().lower() if exp.description else "",
        )
        groups[key].append(exp)

    seen_keys = set()
    subscriptions = []

    # First: include any expense explicitly marked as a subscription
    for exp in expenses:
        if exp.is_subscription:
            key = (
                exp.category.strip().lower(),
                exp.description.strip().lower() if exp.description else "",
            )
            if key not in seen_keys:
                seen_keys.add(key)
                items = groups[key]
                amounts = [i.amount for i in items]
                avg_amount = sum(amounts) / len(amounts)
                subscriptions.append(
                    {
                        "category": exp.category.strip(),
                        "description": exp.description or "No description",
                        "avg_amount": avg_amount,
                        "frequency": len(items),
                        "last_date": max(i.date for i in items),
                        "expenses": items,
                    }
                )

    # Second: auto-detect by repeated pattern (same category+description, 2+ times, similar amount)
    for (cat, desc), items in groups.items():
        key = (cat, desc)
        if key in seen_keys:
            continue
        if len(items) >= 2:
            amounts = [i.amount for i in items]
            avg_amount = sum(amounts) / len(amounts)
            if all(abs(a - avg_amount) <= avg_amount * 0.1 for a in amounts):
                seen_keys.add(key)
                subscriptions.append(
                    {
                        "category": cat,
                        "description": desc or "No description",
                        "avg_amount": avg_amount,
                        "frequency": len(items),
                        "last_date": max(i.date for i in items),
                        "expenses": items,
                    }
                )

    return subscriptions


# Helper: get spending reduction suggestions
def get_spending_suggestions(user_id, goal):
    # Get last 3 months of expenses
    since_date = datetime.utcnow() - timedelta(days=90)
    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= since_date,
        Expense.is_essential == False,  # Only non-essential expenses
    ).all()

    # Group by category and sum
    category_totals = defaultdict(float)
    for exp in expenses:
        category_totals[exp.category] += exp.amount

    # Sort by amount (highest first)
    suggestions = []
    for category, amount in sorted(
        category_totals.items(), key=lambda x: x[1], reverse=True
    )[:5]:
        monthly_avg = amount / 3  # Average monthly spending

        # Suggest reducing by 20% as a starting point
        reduction = monthly_avg * 0.2
        months_saved = (
            goal.remaining_amount / (goal.monthly_savings + reduction)
            if goal.monthly_savings > 0
            else float("inf")
        )
        original_months = goal.estimated_months

        if months_saved != float("inf"):
            time_saved = original_months - months_saved
            suggestions.append(
                {
                    "category": category,
                    "current_spending": monthly_avg,
                    "suggested_reduction": reduction,
                    "new_monthly_savings": goal.monthly_savings + reduction,
                    "months_saved": time_saved,
                    "original_months": original_months,
                    "new_months": months_saved,
                }
            )

    return suggestions


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user)
            if not user.has_seen_tutorial:
                return redirect(url_for("tutorial"))
            return redirect(url_for("dashboard"))
        else:
            flash("Login failed. Check username and password.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/tutorial")
@login_required
def tutorial():
    return render_template("tutorial.html")


@app.route("/complete_tutorial")
@login_required
def complete_tutorial():
    current_user.has_seen_tutorial = True
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    # Expenses this month
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id, Expense.date >= month_start
    ).all()
    total_spent = sum(e.amount for e in expenses)
    essential_spent = sum(e.amount for e in expenses if e.is_essential)
    non_essential_spent = total_spent - essential_spent
    needs_pct = (essential_spent / total_spent * 100) if total_spent else 0
    wants_pct = (non_essential_spent / total_spent * 100) if total_spent else 0
    wants_alert = wants_pct > 50

    # Category breakdown
    categories = {}
    for e in expenses:
        categories[e.category] = categories.get(e.category, 0) + e.amount

    # Income this month
    incomes = Income.query.filter(
        Income.user_id == current_user.id, Income.date_received >= month_start
    ).all()
    total_income = sum(i.amount for i in incomes)
    source_breakdown = {}
    for inc in incomes:
        source_breakdown[inc.source] = source_breakdown.get(inc.source, 0) + inc.amount
    source_percentages = {
        src: (amt / total_income * 100) if total_income else 0
        for src, amt in source_breakdown.items()
    }

    # Recent incomes
    recent_incomes = (
        Income.query.filter_by(user_id=current_user.id)
        .order_by(Income.date_received.desc())
        .limit(10)
        .all()
    )
    # Recent expenses
    recent_expenses = (
        Expense.query.filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .limit(10)
        .all()
    )

    # Burn rate
    days_passed = (now - month_start).days + 1
    burn_rate = total_spent / days_passed if days_passed > 0 else 0

    # Subscriptions (detected)
    subscriptions = detect_subscriptions(current_user.id)
    total_sub_cost = sum(s["avg_amount"] for s in subscriptions)

    # Goals
    goals = (
        Goal.query.filter_by(user_id=current_user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )

    from collections import defaultdict

    monthly_spending = defaultdict(float)

    for exp in expenses:
        month = exp.date.strftime("%b")
        monthly_spending[month] += exp.amount

    essential = 0
    non_essential = 0

    for exp in expenses:
        if exp.is_essential:
            essential += exp.amount
        else:
            non_essential += exp.amount

    total = essential + non_essential

    if total > 0:
        needs_pct = (essential / total) * 100
        wants_pct = (non_essential / total) * 100
    else:
        needs_pct = wants_pct = 0

    wants_alert = wants_pct > 50

    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_spent=total_spent,
        burn_rate=burn_rate,
        source_breakdown=source_breakdown,
        source_percentages=source_percentages,
        essential=essential,
        non_essential=non_essential,
        needs_pct=needs_pct,
        wants_pct=wants_pct,
        wants_alert=wants_alert,
        categories=categories,
        subscriptions=subscriptions,
        total_sub_cost=total_sub_cost,
        recent_incomes=recent_incomes,
        recent_expenses=recent_expenses,
        # ✅ ADD THIS LINE
        monthly_spending=dict(monthly_spending),
    )


@app.route("/add_income", methods=["GET", "POST"])
@login_required
def add_income():
    form = IncomeForm()
    if form.validate_on_submit():
        income = Income(
            user_id=current_user.id,
            source=form.source.data,
            amount=form.amount.data,
            description=form.description.data,
        )
        db.session.add(income)
        db.session.commit()
        flash("Income added successfully!", "success")
        return redirect(url_for("dashboard"))
    incomes = (
        Income.query.filter_by(user_id=current_user.id)
        .order_by(Income.date_received.desc())
        .all()
    )
    return render_template("add_income.html", form=form, edit=False, incomes=incomes)


@app.route("/edit_income/<int:id>", methods=["GET", "POST"])
@login_required
def edit_income(id):
    income = Income.query.get_or_404(id)
    if income.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))
    form = IncomeForm()
    if form.validate_on_submit():
        income.source = form.source.data
        income.amount = form.amount.data
        income.description = form.description.data
        db.session.commit()
        flash("Income updated.", "success")
        return redirect(url_for("dashboard"))
    elif request.method == "GET":
        form.source.data = income.source
        form.amount.data = income.amount
        form.description.data = income.description
    return render_template("add_income.html", form=form, edit=True)


@app.route("/delete_income/<int:id>")
@login_required
def delete_income(id):
    income = Income.query.get_or_404(id)
    if income.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))
    db.session.delete(income)
    db.session.commit()
    flash("Income deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/get_subcategories/<main_category>")
@login_required
def get_subcategories(main_category):
    if main_category in expense_categories:
        return jsonify(
            {
                "subcategories": expense_categories[main_category]["subcategories"],
                "status": "success",
            }
        )
    return jsonify({"subcategories": [], "status": "error"})


@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():
    form = ExpenseForm()
    form.main_category.choices = [("", "-- Select Category --")] + [
        (cat, cat) for cat in expense_categories.keys()
    ]

    if request.method == "POST" and form.main_category.data:
        main_cat = form.main_category.data
        if main_cat in expense_categories:
            subcats = expense_categories[main_cat]["subcategories"]
            form.sub_category.choices = [("", "-- Select Sub Category --")] + [
                (sub, sub) for sub in subcats
            ]

    if request.method == "POST":
        if form.validate_on_submit():
            if (
                form.sub_category.data == "Other (User Input)"
                and form.custom_category.data
            ):
                category = form.custom_category.data
            else:
                category = form.sub_category.data

            is_essential = classify_essential(
                form.main_category.data,
                form.sub_category.data,
                form.custom_category.data,
            )

            expense = Expense(
                user_id=current_user.id,
                category=category,
                amount=form.amount.data,
                description=form.description.data,
                is_essential=is_essential,
                is_subscription=form.is_subscription.data,
            )
            db.session.add(expense)
            db.session.commit()
            flash("Expense added successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            print("Form errors:", form.errors)
            flash("Please check the form and try again.", "danger")
    else:
        form.sub_category.choices = [("", "-- Select Sub Category First --")]

    expenses = (
        Expense.query.filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .all()
    )
    return render_template("add_expense.html", form=form, edit=False, expenses=expenses)


@app.route("/edit_expense/<int:id>", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    expense = Expense.query.get_or_404(id)
    if expense.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))

    form = ExpenseForm()
    form.main_category.choices = [("", "-- Select Category --")] + [
        (cat, cat) for cat in expense_categories.keys()
    ]

    if request.method == "POST" and form.main_category.data:
        main_cat = form.main_category.data
        if main_cat in expense_categories:
            subcats = expense_categories[main_cat]["subcategories"]
            form.sub_category.choices = [("", "-- Select Sub Category --")] + [
                (sub, sub) for sub in subcats
            ]

    if form.validate_on_submit():
        if form.sub_category.data == "Other (User Input)" and form.custom_category.data:
            category = form.custom_category.data
        else:
            category = form.sub_category.data

        expense.category = category
        expense.amount = form.amount.data
        expense.description = form.description.data
        expense.is_subscription = form.is_subscription.data
        expense.is_essential = classify_essential(
            form.main_category.data, form.sub_category.data, form.custom_category.data
        )

        db.session.commit()
        flash("Expense updated.", "success")
        return redirect(url_for("dashboard"))

    elif request.method == "GET":
        main_cat = None
        for cat, data in expense_categories.items():
            if expense.category in data["subcategories"]:
                main_cat = cat
                break

        if main_cat:
            subcats = expense_categories[main_cat]["subcategories"]
            form.sub_category.choices = [("", "-- Select Sub Category --")] + [
                (sub, sub) for sub in subcats
            ]
            form.main_category.data = main_cat
            form.sub_category.data = expense.category
        else:
            form.sub_category.choices = [
                ("", "-- Select Sub Category --"),
                ("Other (User Input)", "Other (User Input)"),
            ]
            form.main_category.data = "Other"
            form.sub_category.data = "Other (User Input)"
            form.custom_category.data = expense.category

        form.amount.data = expense.amount
        form.description.data = expense.description
        form.is_subscription.data = expense.is_subscription

    return render_template("add_expense.html", form=form, edit=True)


@app.route("/delete_expense/<int:id>")
@login_required
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    if expense.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("dashboard"))
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/subscriptions")
@login_required
def subscriptions():
    subs = detect_subscriptions(current_user.id)
    total_cost = sum(s["avg_amount"] for s in subs)
    return render_template(
        "subscriptions.html", subscriptions=subs, total_cost=total_cost
    )


@app.route("/goals")
@login_required
def goals():
    goals = (
        Goal.query.filter_by(user_id=current_user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )
    return render_template("goals.html", goals=goals)


@app.route("/add_goal", methods=["GET", "POST"])
@login_required
def add_goal():
    form = GoalForm()
    if form.validate_on_submit():
        goal = Goal(
            user_id=current_user.id,
            name=form.name.data,
            target_amount=form.target_amount.data,
            monthly_savings=form.monthly_savings.data,
            target_date=form.target_date.data,
        )
        db.session.add(goal)
        db.session.commit()
        flash("Goal created successfully!", "success")
        return redirect(url_for("goals"))
    goals = (
        Goal.query.filter_by(user_id=current_user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )
    return render_template("add_goal.html", form=form, goals=goals)


@app.route("/goal/<int:id>", methods=["GET", "POST"])
@login_required
def goal_detail(id):
    goal = Goal.query.get_or_404(id)
    if goal.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("goals"))

    form = SavingsUpdateForm()
    if form.validate_on_submit():
        # Add the new amount to existing saved amount instead of replacing
        additional_savings = form.saved_amount.data
        goal.saved_amount = goal.saved_amount + additional_savings
        db.session.commit()
        flash(
            f"Added ₹{additional_savings:,.0f} to your savings! Total saved: ₹{goal.saved_amount:,.0f}",
            "success",
        )
        return redirect(url_for("goal_detail", id=id))

    # Get spending reduction suggestions
    suggestions = get_spending_suggestions(current_user.id, goal)

    # Calculate timeline milestones
    milestones = []
    if goal.monthly_savings > 0:
        for month in range(1, min(13, int(goal.estimated_months) + 1)):
            milestone_date = datetime.utcnow() + timedelta(days=30 * month)
            milestone_amount = goal.saved_amount + (goal.monthly_savings * month)
            milestones.append(
                {
                    "month": month,
                    "date": milestone_date,
                    "amount": min(milestone_amount, goal.target_amount),
                }
            )

    return render_template(
        "goal_detail.html",
        goal=goal,
        form=form,
        suggestions=suggestions,
        milestones=milestones,
    )


@app.route("/goal/<int:id>/delete")
@login_required
def delete_goal(id):
    goal = Goal.query.get_or_404(id)
    if goal.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("goals"))

    db.session.delete(goal)
    db.session.commit()
    flash("Goal deleted.", "success")
    return redirect(url_for("goals"))


@app.route("/what_if/<int:id>", methods=["POST"])
@login_required
def what_if(id):
    goal = Goal.query.get_or_404(id)
    if goal.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    new_monthly_savings = data.get("monthly_savings", goal.monthly_savings)
    spending_reduction = data.get("spending_reduction", 0)

    total_monthly = new_monthly_savings + spending_reduction
    if total_monthly <= 0:
        return jsonify(
            {"months": float("inf"), "date": None, "progress": goal.progress_percentage}
        )

    remaining = goal.remaining_amount
    months = remaining / total_monthly

    from datetime import timedelta

    estimated_date = datetime.utcnow() + timedelta(days=30 * months)

    return jsonify(
        {
            "months": round(months, 1),
            "date": estimated_date.strftime("%d %b %Y"),
            "progress": goal.progress_percentage,
        }
    )


@app.route("/analysis")
@login_required
def analysis():
    return render_template("analysis.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
