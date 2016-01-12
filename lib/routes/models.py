import os
from ..db import db
from ..models import Model, User
from ..excs import ModelNotFoundException, ModelConflictException
from flask import Blueprint, send_from_directory, jsonify, request, abort
from flask_security import auth_token_required

bp = Blueprint('models', __name__, url_prefix='/models')


def validate_owner(model, request):
    """validates model ownership via auth token"""
    auth_token = request.headers.get('Authentication-Token')
    if model.owner.get_auth_token() != auth_token:
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
            return jsonify(status='success')
        except ModelConflictException as e:
            return jsonify(status='failure', reason=str(e)), 400

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
    user = User.query.filter_by(name=data['user']).first()
    auth_token = request.headers.get('Authentication-Token')
    if user is None or user.get_auth_token() != auth_token:
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