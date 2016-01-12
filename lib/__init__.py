import os
import config
from .routes import models_bp
from .db import db
from flask import Flask
from flask_migrate import Migrate
from flask_security import SQLAlchemyUserDatastore, Security


def create_app(package_name=__name__, **config_overrides):
    app = Flask(package_name)
    app.config.from_object(config)

    # Apply overrides
    app.config.update(config_overrides)

    # Initialize the database and declarative Base class
    db.init_app(app)
    Migrate(app, db)

    # Setup security
    from . import models
    app.user_db = SQLAlchemyUserDatastore(db, models.User, models.Role)
    Security(app, app.user_db)

    # Create the database tables.
    # Flask-SQLAlchemy needs to know which
    # app context to create the tables in.
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(models_bp)

    # Create repo/archive dirs
    for dir in [app.config['REPO_DIR'], app.config['ARCHIVE_DIR']]:
        if not os.path.exists(dir):
            os.makedirs(dir)

    return app
