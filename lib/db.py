from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_searchable import make_searchable

db = SQLAlchemy(session_options={'autoflush': False})
make_searchable()
