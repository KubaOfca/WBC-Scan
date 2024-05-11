import os
from pathlib import Path

from flask_login import UserMixin
from sqlalchemy import event
from sqlalchemy.orm import relationship

from . import db


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    name = db.Column(db.String(150))
    password = db.Column(db.String(150))
    secret_key = db.Column(db.String(32))


class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    date = db.Column(db.DateTime(timezone=True))
    image = relationship("Image", backref="user", cascade='all, delete')


class Batch(db.Model):
    __tablename__ = 'batch'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    name = db.Column(db.String(100))


class Image(db.Model):
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))
    name = db.Column(db.String(100))
    date = db.Column(db.DateTime(timezone=True))
    image = db.Column(db.String(1000))
    annotated_image = db.Column(db.String(1000), default=None)


class Stats(db.Model):
    __tablename__ = 'stats'
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, default=0)
    class_name = db.Column(db.String(100), default="Unknown")
    count = db.Column(db.Integer, default=0)


class MlModels(db.Model):
    __tablename__ = 'models'
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(500))
    name = db.Column(db.String(100))


@event.listens_for(MlModels.__table__, 'after_create')
def init_models(*args, **kwargs):
    for model_path in os.listdir(os.path.join(Path(__file__).parent.parent, "ml_models")):
        if not is_model_exists_in_db(model_path):
            db.session.add(
                MlModels(model=os.path.join(Path(__file__).parent.parent, "ml_models", model_path), name=model_path))
            db.session.commit()


def is_model_exists_in_db(model_path):
    existing_model = MlModels.query.filter_by(model=model_path).first()
    return existing_model is not None
