"""Blueprint registration."""
from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .admin import bp as admin_bp
    from .api import bp as api_bp
    from .applications import bp as applications_bp
    from .auth import bp as auth_bp
    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
