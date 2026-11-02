from __future__ import annotations

import pytest

from app import create_app
from config import Config
from extensions import db
from tests.helpers import make_user


@pytest.fixture()
def app(tmp_path):
    class TestingConfig(Config):
        TESTING = True
        SECRET_KEY = "test-only-secret-key-do-not-use-in-production"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        AUTO_CREATE_DB = True
        WTF_CSRF_ENABLED = True
        APPLICATIONS_PER_PAGE = 2
        ADMIN_APPLICATIONS_PER_PAGE = 2

    application = create_app(TestingConfig)
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_id(app):
    return make_user(app)


@pytest.fixture()
def admin_id(app):
    return make_user(
        app,
        name="System Administrator",
        email="admin@example.com",
        password="AdminPass1",
        role="admin",
    )
