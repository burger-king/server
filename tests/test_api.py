import os
import io
import json
import shutil
import tarfile
import unittest
from lib import create_app
from lib.db import db
from lib.models import User, Model

test_config = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'postgresql://bk_user:password@localhost:5432/bk_test',
    'REPO_DIR': '/tmp/test_repos',
    'ARCHIVE_DIR': '/tmp/test_archives'
}


class APITest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(**test_config)
        self.client = self.app.test_client()
        self.db = db

        self._ctx = self.app.test_request_context()
        self._ctx.push()

        with self.app.app_context():
            self.db.create_all()

        # create test model
        self.model_name = 'test_model'
        self.model = Model(self.model_name)

        # create test user
        self.user = User(email='yo@sup.com', password='password', name='sup')
        self.model.register(self.user)
        self.db.session.add(self.user)
        self.db.session.add(self.model)
        self.db.session.commit()

    def tearDown(self):
        for dir in [test_config['REPO_DIR'], test_config['ARCHIVE_DIR']]:
            shutil.rmtree(dir)

        if self._ctx is not None:
            self._ctx.pop()

        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()

        del self.app
        del self.client
        del self._ctx


    def _make_user(self):
        user = User(email='yo2@sup.com', password='password', name='sup2')
        self.db.session.add(user)
        self.db.session.commit()
        return user

    def _publish_model(self, version):
        meta = {'version': version}
        model = {'params': [1,1,1]}
        self.model.publish(meta, model, version)
        self.model.make_archive(version)
        return meta, model

    def _extract_tar(self, data):
        # extract files to disk
        tar = tarfile.open(fileobj=io.BytesIO(data))
        tar.extractall('/tmp/')
        with open('/tmp/meta.json', 'r') as f:
            meta = json.load(f)
        with open('/tmp/model.json', 'r') as f:
            model = json.load(f)
        return meta, model

    def _request(self, method, endpoint, auth=None, data=None):
        kwargs = {
            'headers': [('Content-Type', 'application/json')]
        }
        if auth is not None:
            kwargs['headers'].append(('Authentication-Token', auth))
        if data is not None:
            kwargs['data'] = json.dumps(data)
        return getattr(self.client, method.lower())(endpoint, **kwargs)

    def test_get_model_without_archives(self):
        resp = self._request('GET', '/models/{}'.format(self.model_name))
        self.assertEquals(resp.status_code, 404)

    def test_get_nonexistent_model(self):
        resp = self._request('GET', '/models/sup')
        self.assertEquals(resp.status_code, 404)

    def test_publish_model(self):
        meta = {'version': '1.0.0'}
        model = {'params': [1,1,1]}
        resp = self._request('POST', '/models/{}'.format(self.model_name),
                             auth=self.user.get_auth_token(),
                             data={'meta': meta, 'model': model})
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(self.model.latest, '1.0.0')

        # check that all files are there and proper
        repo_path = os.path.join(test_config['REPO_DIR'], self.model_name)
        archive_path = os.path.join(test_config['ARCHIVE_DIR'], self.model_name, '1.0.0.tar')
        meta_path = os.path.join(repo_path, 'meta.json')
        model_path = os.path.join(repo_path, 'model.json')
        for path in [archive_path, repo_path, meta_path, model_path]:
            self.assertTrue(os.path.exists(path))
        self.assertEquals(json.load(open(meta_path, 'r')), meta)
        self.assertEquals(json.load(open(model_path, 'r')), model)

    def test_publish_model_not_owner(self):
        meta = {'version': '1.0.0'}
        model = {'params': [1,1,1]}
        resp = self._request('POST', '/models/{}'.format(self.model_name),
                             auth='sup',
                             data={'meta': meta, 'model': model})
        self.assertEquals(resp.status_code, 401)

    def test_publish_model_invalid_version(self):
        self._publish_model('1.0.0')
        meta = {'version': '0.0.5'}
        model = {'params': [1,1,1]}
        resp = self._request('POST', '/models/{}'.format(self.model_name),
                             auth=self.user.get_auth_token(),
                             data={'meta': meta, 'model': model})
        self.assertEquals(resp.status_code, 400)
        self.assertEquals(self.model.latest, '1.0.0')

    def test_get_model(self):
        meta, model = self._publish_model('1.0.0')

        resp = self._request('GET', '/models/{}'.format(self.model_name))
        self.assertEquals(resp.status_code, 200)
        meta_, model_ = self._extract_tar(resp.data)
        self.assertEquals(meta, meta_)
        self.assertEquals(model, model_)

    def test_get_model_specific_version(self):
        meta_old, model_old = self._publish_model('1.0.0')
        meta_new, model_new = self._publish_model('2.0.0')

        # get latest
        resp = self._request('GET', '/models/{}'.format(self.model_name))
        self.assertEquals(resp.status_code, 200)
        meta_, model_ = self._extract_tar(resp.data)
        self.assertEquals(meta_new, meta_)
        self.assertEquals(model_new, model_)

        # get specific version
        resp = self._request('GET', '/models/{}/1.0.0'.format(self.model_name))
        self.assertEquals(resp.status_code, 200)
        meta_, model_ = self._extract_tar(resp.data)
        self.assertEquals(meta_old, meta_)
        self.assertEquals(model_old, model_)

    def test_get_model_meta(self):
        meta, model = self._publish_model('1.0.0')
        resp = self._request('GET', '/models/{}.json'.format(self.model_name))
        self.assertEquals(resp.status_code, 200)
        resp_json = json.loads(resp.data.decode('utf-8'))
        self.assertEquals(resp_json, meta)

    def test_delete_version_not_owner(self):
        meta, model = self._publish_model('1.0.0')
        resp = self._request('DELETE', '/models/{}/1.0.0'.format(self.model_name),
                             auth='sup')
        self.assertEquals(resp.status_code, 401)

    def test_delete_nonexistent_version(self):
        meta, model = self._publish_model('1.0.0')
        resp = self._request('DELETE', '/models/{}/2.0.0'.format(self.model_name),
                             auth=self.user.get_auth_token())
        self.assertEquals(resp.status_code, 404)

    def test_delete_version(self):
        self._publish_model('1.0.0')
        self._publish_model('2.0.0')
        resp = self._request('DELETE', '/models/{}/1.0.0'.format(self.model_name),
                             auth=self.user.get_auth_token())
        self.assertEquals(resp.status_code, 200)

        # check that archive is gone
        archive_path = os.path.join(test_config['ARCHIVE_DIR'], self.model_name, '1.0.0.tar')
        self.assertFalse(os.path.exists(archive_path))

    def test_remove_model(self):
        self._publish_model('1.0.0')
        resp = self._request('DELETE', '/models/{}'.format(self.model_name),
                             auth=self.user.get_auth_token())
        self.assertEquals(resp.status_code, 200)

        # check that everything is gone
        archive_path = os.path.join(test_config['ARCHIVE_DIR'], self.model_name)
        repo_path = os.path.join(test_config['REPO_DIR'], self.model_name)
        self.assertFalse(os.path.exists(archive_path))
        self.assertFalse(os.path.exists(repo_path))

    def test_change_ownership(self):
        self._publish_model('1.0.0')
        user = self._make_user()
        resp = self._request('PUT', '/models/{}'.format(self.model_name),
                             auth=self.user.get_auth_token(),
                             data={'user': user.name})
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(self.model.owner, user)

    def test_change_ownership_nonexistent_user(self):
        self._publish_model('1.0.0')
        resp = self._request('PUT', '/models/{}'.format(self.model_name),
                             auth=self.user.get_auth_token(),
                             data={'user': 'sup2'})
        self.assertEquals(resp.status_code, 404)

    def test_register_model(self):
        resp = self._request('POST', '/models/register',
                             auth=self.user.get_auth_token(),
                             data={'user': self.user.name, 'name': 'new_model'})
        self.assertEquals(resp.status_code, 200)

    def test_register_existing_model(self):
        resp = self._request('POST', '/models/register',
                             auth=self.user.get_auth_token(),
                             data={'user': self.user.name, 'name': self.model.name})
        self.assertEquals(resp.status_code, 409)

    def test_register_unauthenticated(self):
        resp = self._request('POST', '/models/register',
                             data={'user': self.user.name, 'name': self.model.name})
        self.assertEquals(resp.status_code, 401)
