"""Create and configure the Flask application."""
from flask_cors import CORS
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException

db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object("config.Config")

    required_settings = ("SECRET_KEY", "JWT_SECRET_KEY", "SQLALCHEMY_DATABASE_URI")
    missing_settings = [
        setting for setting in required_settings if not app.config.get(setting)
    ]
    if missing_settings:
        raise RuntimeError(
            "Missing required .env settings: " + ", ".join(missing_settings)
        )

    db.init_app(app)
    jwt.init_app(app)

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify(error="A valid access token is required."), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify(error="The access token is invalid."), 401

    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_payload):
        return jsonify(error="The access token has expired."), 401

    @jwt.needs_fresh_token_loader
    def fresh_token_required(_jwt_header, _jwt_payload):
        return jsonify(error="A fresh access token is required."), 401

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(500)
    def handle_server_error(error):
        original_error = getattr(error, "original_exception", None)
        if original_error is not None:
            app.logger.error(
                "Unhandled server error",
                exc_info=(
                    type(original_error),
                    original_error,
                    original_error.__traceback__,
                ),
            )
        else:
            app.logger.error("Unhandled server error: %s", error)
        return jsonify(error="An unexpected server error occurred."), 500

    from app.routes.auth import auth_bp
    from app.routes.expenses import expenses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)

    return app