import json
import shutil
from lib.db import db
from git import Repo, Actor
from datetime import datetime
from flask import current_app
from flask_sqlalchemy import BaseQuery
from os import path, makedirs, remove
from distutils.version import LooseVersion
from sqlalchemy_searchable import SearchQueryMixin
from sqlalchemy_utils.types import TSVectorType
from lib.excs import ModelNotFoundException, ModelConflictException


class ModelQuery(BaseQuery, SearchQueryMixin):
    pass


class Model(db.Model):
    __tablename__   = 'model'
    query_class     = ModelQuery
    id              = db.Column(db.Integer(), primary_key=True)
    name            = db.Column(db.Unicode(255), unique=True)
    description     = db.Column(db.Unicode())
    owner           = db.relationship('User')
    owner_id        = db.Column(db.Integer(), db.ForeignKey('user.id'))
    created_at      = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime(), default=datetime.utcnow)
    search_vector   = db.Column(TSVectorType('name', 'description'))

    def __init__(self, name):
        self.name = name

    @property
    def repo_path(self):
        return path.join(current_app.config['REPO_DIR'], self.name)

    @property
    def archive_path(self):
        return path.join(current_app.config['ARCHIVE_DIR'], self.name)

    @property
    def meta_path(self):
        return path.join(self.repo_path, 'meta.json')

    @property
    def model_path(self):
        return path.join(self.repo_path, 'model.json')

    @property
    def repo(self):
        return Repo(self.repo_path) if path.exists(self.repo_path) else None

    def register(self, user):
        """registers the model to the specified user"""
        self.owner = user
        if self.repo is None:
            self.make_repo()

    def archive(self, version=None):
        """returns path for a specific version's archive.
        if version is None, returns latest version"""
        if self.repo is None:
            raise ModelNotFoundException

        if version is None:
            version = self.latest
        if version not in self.versions:
            raise ModelNotFoundException
        return path.join(self.archive_path, '{}.tar'.format(version))

    def make_repo(self):
        """creates a new git repo for the model,
        if it doesn't already exist"""
        if path.exists(self.repo_path):
            raise ModelConflictException
        Repo.init(self.repo_path)

    @property
    def latest(self):
        """returns the latest version"""
        if not self.versions:
            return None
        return self.versions[-1]

    @property
    def versions(self):
        """all available versions"""
        repo = self.repo
        if repo is None or not repo.tags:
            return []
        return [tag.name for tag in repo.tags]

    def publish(self, meta_data, model_data, version):
        """updates a repo for the model (publishes a new version)"""
        repo = self.repo
        if repo is None:
            raise ModelNotFoundException

        # the new version must be the newest
        if self.latest is not None and LooseVersion(self.latest) >= LooseVersion(version):
            raise ModelConflictException('Published version must be newer than {}'.format(self.latest))

        with open(self.meta_path, 'w') as f:
            json.dump(meta_data, f)

        # TODO this should be PMML or something
        with open(self.model_path, 'w') as f:
            json.dump(model_data, f)

        repo.index.add(['*'])
        author = Actor(self.owner.name, self.owner.email)
        repo.index.commit(version, author=author, committer=author)
        repo.create_tag(version)
        self.description = meta_data.get('description', '')
        self.updated_at = datetime.utcnow()

    def make_archive(self, version):
        """creates a tar archive for a specific version of the model"""
        if not path.exists(self.archive_path):
            makedirs(self.archive_path)
        self.repo.archive(open(self.archive(version), 'wb'), version)

    def delete(self, version):
        """deletes a specific version"""
        if version not in self.versions:
            raise ModelNotFoundException
        remove(self.archive(version))
        self.repo.delete_tag(version)

    def destroy(self):
        """destroys the entire package"""
        shutil.rmtree(self.repo_path)
        shutil.rmtree(self.archive_path)

    @property
    def meta(self):
        """model metadata"""
        return json.load(open(self.meta_path, 'r'))
