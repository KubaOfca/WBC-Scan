from flask_login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy import event
from . import db, s3_client


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    name = db.Column(db.String(150))
    password = db.Column(db.String(250))
    secret_key = db.Column(db.String(32))
    project_r = relationship(
        'Project',
        back_populates='user',
        cascade='save-update, merge, delete',
        passive_deletes=True,
    )


class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    name = db.Column(db.String(100))
    date = db.Column(db.DateTime(timezone=True))
    batch_r = relationship(
        'Batch',
        back_populates='project',
        cascade='save-update, merge, delete',
        passive_deletes=True,
    )
    image_r = relationship(
        'Image',
        back_populates='project',
        cascade='save-update, merge, delete',
        passive_deletes=True,
    )
    user = relationship(
        'User',
        back_populates='project_r',
    )


class Batch(db.Model):
    __tablename__ = 'batch'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'))
    name = db.Column(db.String(100))
    project = relationship(
        'Project',
        back_populates='batch_r',
    )
    image_r = relationship(
        'Image',
        back_populates='batch',
        cascade='save-update, merge, delete',
        passive_deletes=False,
    )


class Image(db.Model):
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'))
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id', ondelete='CASCADE'))
    name = db.Column(db.String(100))
    date = db.Column(db.DateTime(timezone=True))
    image = db.Column(db.String(1000))
    annotated_image = db.Column(db.String(1000), default=None)
    project = relationship(
        'Project',
        back_populates='image_r',
    )
    batch = relationship(
        'Batch',
        back_populates='image_r',
    )
    stats_r = relationship(
        'Stats',
        back_populates='image',
        cascade='save-update, merge, delete',
        passive_deletes=True,
    )


class Stats(db.Model):
    __tablename__ = 'stats'
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id', ondelete='CASCADE'))
    class_id = db.Column(db.Integer)
    class_name = db.Column(db.String(100), default="Unknown")
    box_coords = db.Column(db.String(100))
    image = relationship(
        'Image',
        back_populates='stats_r',
    )


class MlModels(db.Model):
    __tablename__ = 'models'
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(500))
    name = db.Column(db.String(100))


# @event.listens_for(MlModels.__table__, 'after_create')
# def init_models(*args, **kwargs):
#     for model_path in os.listdir(os.path.join(Path(__file__).parent.parent, "ml_models")):
#         # if not is_model_exists_in_db(model_path):
#         db.session.add(
#             MlModels(model=os.path.join(Path(__file__).parent.parent, "ml_models", model_path), name=model_path))
#         db.session.commit()


def is_model_exists_in_db(model_path):
    existing_model = MlModels.query.filter_by(model=model_path).first()
    return existing_model is not None

@db.event.listens_for(Image, "after_delete")
def after_delete_listener(mapper, connection, target):
    s3_key = target.image
    try:
        s3_client.delete_object(Bucket='wbc-app', Key=s3_key)
    except Exception as e:
        print("Error deleting")

@db.event.listens_for(Batch, 'after_delete')
def after_batch_delete(mapper, connection, target):
    # Iterate over the associated images and delete from S3
    #raise RuntimeError(target.image_r)
    for image in target.image_r:
        try:
            s3_client.delete_object(Bucket='wbc-app', Key=image.image)
        except Exception as e:
            print(f"Error deleting object from S3: {e}")
