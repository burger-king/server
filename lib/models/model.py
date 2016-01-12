import json
import shutil
from ..db import db
from git import Repo, Actor
from flask import current_app
from os import path, makedirs, remove
from distutils.version import LooseVersion
from ..excs import ModelNotFoundException, ModelConflictException


class Model(db.Model):
    __tablename__   = 'model'
    id              = db.Column(db.Integer(), primary_key=True)
    name            = db.Column(db.String(255), unique=True)
    owner           = db.relationship('User')
    owner_id        = db.Column(db.Integer(), db.ForeignKey('user.id'))

    def __init__(self, name):
        self.name = name
        self.repo_path = path.join(current_app.config['REPO_DIR'], self.name)
        self.archive_path = path.join(current_app.config['ARCHIVE_DIR'], self.name)
        self.meta_path = path.join(self.repo_path, 'meta.json')
        self.model_path = path.join(self.repo_path, 'model.json')
        self.repo = Repo(self.repo_path) if path.exists(self.repo_path) else None

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
        self.repo = Repo.init(self.repo_path)

    @property
    def latest(self):
        """returns the latest version"""
        if not self.versions:
            return None
        return self.versions[-1]

    @property
    def versions(self):
        """all available versions"""
        if self.repo is None or not self.repo.tags:
            return []
        return [tag.name for tag in self.repo.tags]

    def publish(self, meta_data, model_data, version):
        """updates a repo for the model (publishes a new version)"""
        if self.repo is None:
            raise ModelNotFoundException

        # the new version must be the newest
        if self.latest is not None and LooseVersion(self.latest) >= LooseVersion(version):
            raise ModelConflictException('Published version must be newer than {}'.format(self.latest))

        with open(self.meta_path, 'w') as f:
            json.dump(meta_data, f)

        # TODO this should be PMML or something
        with open(self.model_path, 'w') as f:
            json.dump(model_data, f)

        self.repo.index.add(['*'])
        author = Actor(self.owner.name, self.owner.email)
        self.repo.index.commit(version, author=author, committer=author)
        self.repo.create_tag(version)

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
