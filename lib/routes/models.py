import os
from lib.db import db
from lib.models import Model, User
from lib.excs import ModelNotFoundException, ModelConflictException
from flask import Blueprint, send_from_directory, jsonify, request, abort
from flask_security import auth_token_required
from flask_security.core import _token_loader

bp = Blueprint('models', __name__, url_prefix='/models')


def validate_owner(model, request):
    """validates model ownership via auth token"""
    auth_token = request.headers.get('Authentication-Token')
    user = _token_loader(auth_token)
    if model.owner != user:
        abort(401)


@bp.route('/<name>', methods=['GET', 'POST', 'DELETE', 'PUT'])
def model(name):
    """variously manage or download models"""
    model = Model.query.filter_by(name=name).first_or_404()

    if request.method == 'POST':
        # update model (publish a new version)
        validate_owner(model, request)

        # TODO validate the data
        # TODO should the model be sent as a separate file, w/ a checksum?
        # TODO client should first validate version stuff before submitting the full model
        data = request.get_json()

        try:
            version = data['meta']['version']
            model.publish(data['meta'], data['model'], version)
            model.make_archive(version)
            db.session.add(model)
            db.session.commit()
            return jsonify(status='success')
        except ModelConflictException as e:
            return jsonify(status='failure', reason=str(e)), 409

    elif request.method == 'DELETE':
        # deletes the entire model package
        validate_owner(model, request)
        model.destroy()
        return jsonify(status='success')

    elif request.method == 'PUT':
        # this is just for changing ownership atm
        validate_owner(model, request)
        data = request.get_json()

        user = User.query.filter_by(name=data['user']).first_or_404()
        model.owner = user
        db.session.add(model)
        db.session.commit()
        return jsonify(status='success')

    else:
        # download archive
        try:
            return send_from_directory(*os.path.split(model.archive()))
        except ModelNotFoundException:
            abort(404)


@bp.route('/<name>/<version>', methods=['GET', 'DELETE'])
def model_version(name, version):
    """manage a specific version of a model package"""
    model = Model.query.filter_by(name=name).first_or_404()

    if request.method == 'DELETE':
        # delete the version
        validate_owner(model, request)
        try:
            model.delete(version)
            return jsonify(status='success')
        except ModelNotFoundException:
            abort(404)
    else:
        # download the version
        try:
            return send_from_directory(*os.path.split(model.archive(version)))
        except ModelNotFoundException:
            abort(404)


@bp.route('/<name>.json')
def model_json(name):
    """return model json metadata"""
    model = Model.query.filter_by(name=name).first_or_404()
    return jsonify(**model.meta)


@bp.route('/register', methods=['POST'])
@auth_token_required
def register():
    """register a model"""
    data = request.get_json()

    # authenticate the user
    name = data['name']

    auth_token = request.headers.get('Authentication-Token')
    user = _token_loader(auth_token)
    if not user.is_authenticated:
        abort(401)

    # confirm no conflicts
    model = Model.query.filter_by(name=name).first()
    if model is not None:
        abort(409)

    model = Model(name)
    model.register(user)
    db.session.add(model)
    db.session.commit()
    return jsonify(status='success')


@bp.route('/search', methods=['POST'])
def search():
    """full-text search models"""
    data = request.get_json()
    query = data['query']
    results = Model.query.search(query, sort=True).limit(50)
    return jsonify(results=[{
        'name': model.name,
        'version': model.latest,
        'description': model.description,
        'updated_at': model.updated_at.isoformat()
    } for model in results])