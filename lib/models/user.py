from lib.db import db
from datetime import datetime
from flask_security import UserMixin, RoleMixin


# Table connecting users and roles
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id              = db.Column(db.Integer(), primary_key=True)
    name            = db.Column(db.Unicode(80), unique=True)
    description     = db.Column(db.Unicode(255))


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id              = db.Column(db.Integer(), primary_key=True)
    name            = db.Column(db.Unicode(255), unique=True)
    email           = db.Column(db.String(255), unique=True)
    password        = db.Column(db.String(255))
    active          = db.Column(db.Boolean())
    confirmed_at    = db.Column(db.DateTime())
    created_at      = db.Column(db.DateTime(), default=datetime.utcnow)
    models          = db.relationship('Model')
    roles           = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
