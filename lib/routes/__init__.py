from .models import bp as models_bp
from .users import bp as users_bp
from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')
