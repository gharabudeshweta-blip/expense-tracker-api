"""Registration and login routes."""

from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import User
from app.utils import (
    error_response,
    read_json_object,
    validate_email,
    validate_name,
    validate_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    data, error = read_json_object()
    if error:
        return error_response(error, 400)

    name, error = validate_name(data.get("name"))
    if error:
        return error_response(error, 400)
    normalized_email, error = validate_email(data.get("email"))
    if error:
        return error_response(error, 400)
    password, error = validate_password(data.get("password"))
    if error:
        return error_response(error, 400)

    if User.query.filter_by(email=normalized_email).first():
        return error_response("An account with this email already exists.", 409)

    user = User(
        name=name,
        email=normalized_email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("An account with this email already exists.", 409)

    return jsonify(message="Account created successfully.", user={
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }), 201


@auth_bp.post("/login")
def login():
    data, error = read_json_object()
    if error:
        return error_response(error, 400)

    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return error_response("Email and password are required.", 400)

    normalized_email, error = validate_email(email)
    if error:
        return error_response(error, 400)
    user = User.query.filter_by(email=normalized_email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return error_response("Invalid email or password.", 401)

    access_token = create_access_token(identity=str(user.id))
    return jsonify(
        message="Login successful.",
        access_token=access_token,
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    ), 200
