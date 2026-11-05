"""Shared request and input validation helpers."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import jsonify, request

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_CATEGORIES = {
    "Food",
    "Travel",
    "Bills",
    "Shopping",
    "Health",
    "Education",
    "Other",
}


def error_response(message, status_code):
    return jsonify(error=message), status_code


def read_json_object():
    """Return a JSON object or a clear validation error."""
    if not request.is_json:
        return None, "A valid JSON object is required."
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, "A valid JSON object is required."
    return data, None


def validate_name(value):
    if not isinstance(value, str) or not value.strip():
        return None, "Name is required."
    name = value.strip()
    if len(name) > 100:
        return None, "Name must be 100 characters or fewer."
    return name, None


def validate_email(value):
    if not isinstance(value, str) or not EMAIL_PATTERN.fullmatch(value.strip()):
        return None, "A valid email address is required."
    return value.strip().lower(), None


def validate_password(value):
    if not isinstance(value, str) or len(value) < 6:
        return None, "Password must be at least 6 characters long."
    return value, None


def parse_iso_date(value, field_name):
    if not isinstance(value, str):
        return None, f"{field_name} must use YYYY-MM-DD format."
    try:
        parsed_date = date.fromisoformat(value)
    except ValueError:
        return None, f"{field_name} must use YYYY-MM-DD format."
    if parsed_date.isoformat() != value:
        return None, f"{field_name} must use YYYY-MM-DD format."
    return parsed_date, None


def parse_positive_integer(value, field_name, maximum=None):
    if not isinstance(value, str) or not value.isdecimal():
        return None, f"{field_name} must be a positive integer."
    parsed_value = int(value)
    if parsed_value < 1:
        return None, f"{field_name} must be a positive integer."
    if maximum is not None and parsed_value > maximum:
        return None, f"{field_name} cannot be greater than {maximum}."
    return parsed_value, None


def validate_expense_data(data):
    """Validate all required expense fields and the optional note."""
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return None, "Title is required."
    title = title.strip()
    if len(title) > 100:
        return None, "Title must be 100 characters or fewer."

    raw_amount = data.get("amount")
    if isinstance(raw_amount, bool) or not isinstance(raw_amount, (int, float)):
        return None, "Amount must be a number greater than 0."
    try:
        amount = Decimal(str(raw_amount))
    except InvalidOperation:
        return None, "Amount must be a number greater than 0."
    if not amount.is_finite() or amount <= 0:
        return None, "Amount must be a number greater than 0."
    if amount > Decimal("99999999.99") or amount.as_tuple().exponent < -2:
        return None, "Amount must fit DECIMAL(10, 2)."

    category = data.get("category")
    if not isinstance(category, str) or category not in ALLOWED_CATEGORIES:
        return None, (
            "Category must be one of: Food, Travel, Bills, Shopping, "
            "Health, Education, Other."
        )

    expense_date, error = parse_iso_date(data.get("expense_date"), "Expense date")
    if error:
        return None, error
    if expense_date > date.today():
        return None, "Expense date cannot be in the future."

    note = data.get("note")
    if note is not None and not isinstance(note, str):
        return None, "Note must be a string."

    return {
        "title": title,
        "amount": amount,
        "category": category,
        "expense_date": expense_date,
        "note": note,
    }, None
