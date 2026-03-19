# Money Mate - Personal Finance Manager

## Overview
A Flask-based personal finance management web application that helps users track income, expenses, savings goals, and subscriptions.

## Tech Stack
- **Backend**: Python 3.12, Flask
- **Database**: SQLite (via Flask-SQLAlchemy)
- **Auth**: Flask-Login
- **Forms**: Flask-WTF / WTForms
- **Admin Panel**: Flask-Admin
- **Frontend**: Jinja2 templates, Bootstrap 5, Chart.js
- **Production Server**: Gunicorn

## Project Structure
- `app.py` - Main Flask application with all routes (738 lines)
- `models.py` - SQLAlchemy models: User, Income, Expense, Goal
- `forms.py` - WTForms form classes
- `templates/` - Jinja2 HTML templates
- `static/` - CSS and static assets
- `finance.db` - SQLite database file
- `requirements.txt` - Python dependencies

## Running the App
- **Development**: `python app.py` (runs on 0.0.0.0:5000)
- **Production**: `gunicorn --bind=0.0.0.0:5000 --reuse-port app:app`

## Key Features
- User registration and login
- Income tracking
- Expense tracking with category/subcategory hierarchy and need/want classification
- Subscription management
- Savings goals with progress tracking
- Financial analysis dashboard
- Admin panel at `/admin` (accessible by user with username 'admin')

## Notes
- Templates must be in the `templates/` directory (Flask convention)
- Static files must be in the `static/` directory
- Admin user can be created by visiting `/create_admin`
