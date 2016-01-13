from flask import Blueprint, render_template
from flask_security import current_user, login_required

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/token')
@login_required
def token():
    token = current_user.get_auth_token()
    return render_template('security/show_token.html', token=token)
