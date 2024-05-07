import base64
import json
import math
import os
from datetime import datetime
from io import BytesIO

import numpy as np
import plotly
import plotly.express as px
from PIL import Image as PILImage
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, session
from flask_login import login_required, current_user
from ultralytics import YOLO

from . import socket, db
from .models import Project, Image, Stats, MlModels
from .utils import get_user_projects, add_project_to_db

views = Blueprint('views', __name__)
IMAGE_TABLE_MAX_ROWS_DISPLAY = 10
RUN_TAB = 1
STATS_TAB = 2
IMAGE_TAB = 3


@views.route('/', methods=["GET", "POST"])
@login_required
def home():
    session["user_name"] = current_user.name
    if request.method == "POST":
        add_project_to_db(user_id=current_user.id, project_name=request.form.get("new-project-name"))
        flash("Project created!", category="success")
        return redirect(url_for("views.home"))  # redirect in order to close POST form (e.g. when refresh)
    return render_template("home.html", user_projects=get_user_projects())


@views.route("/old_project")
def old_project():
    project_id = request.args.get("project_id", 1, type=int)
    tab = request.args.get("tab", 1, type=int)
    page = request.args.get("page", 1, type=int)

    start = (page - 1) * IMAGE_TABLE_MAX_ROWS_DISPLAY
    end = page * page_len

    images = Image.query.filter_by(project_id=project_id)
    images_len = images.count()
    last_page_number = math.ceil(images_len / page_len)
    images_png = []
    images_annotated_png = []
    for image in images[start:end]:
        images_png.append(base64.b64encode(image.image).decode('ascii'))
        try:
            images_annotated_png.append(base64.b64encode(image.annotated_image).decode('ascii'))
        except TypeError:
            images_annotated_png.append(None)
    images_full_info = list(zip(images[start:end], images_png, images_annotated_png))
    stats = Stats.query.filter(Stats.image_id.in_([image.id for image in images]))
    import pandas as pd
    df = pd.read_sql(stats.statement, db.engine)
    df = pd.melt(df, id_vars=['id'], var_name='class_name', value_name='value')
    fig1 = px.bar(df, x="class_name", y="value", title="Wide-Form Input")
    graph1JSON = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template("project.html", project_id=project_id, images=images_full_info, page=page,
                           last_page_number=last_page_number, images_len=images_len, tab=tab,
                           stats=graph1JSON)


@views.route("/project")
def project():
    project_id = request.args.get("project_id", type=int)
    page = request.args.get("page", type=int)
    tab = request.args.get("tab", type=int)
    if project_id is not None:
        session["project_id"] = project_id
    if page is not None:
        if page < 1:
            session["image_page"] = 1
        elif "last_page" in session and page > session["last_page"]:
            session["image_page"] = session["last_page"]
        else:
            session["image_page"] = page
    if tab is not None:
        session["tab"] = tab

    return render_template("project.html", images=get_project_images())


def get_project_images():
    images = Image.query.filter_by(project_id=session["project_id"])
    first_image_on_page = IMAGE_TABLE_MAX_ROWS_DISPLAY * (session["image_page"] - 1)
    last_image_on_page = first_image_on_page + IMAGE_TABLE_MAX_ROWS_DISPLAY
    session["last_page"] = max(math.ceil(images.count() / IMAGE_TABLE_MAX_ROWS_DISPLAY), 1)
    return images[first_image_on_page:last_image_on_page]


@views.route("/upload_images", methods=["POST"])
def upload_images():
    if "images[]" not in request.files:
        flash("No file part", category="error")
        return redirect(url_for("views.project"))

    images = request.files.getlist("images[]")
    for image in images:
        if image.filename == "":
            flash("No selected file", category="error")
            continue
        if image and allowed_file(image.filename):
            new_image = Image(
                project_id=session["project_id"],
                name=image.filename,
                image=image.filename,
                date=datetime.now(),
            )
            print(os.getcwd())
            image.save(
                os.path.join(
                    "website",
                    "static",
                    image.filename,
                )
            )
            db.session.add(new_image)
            db.session.commit()
        else:
            flash("Invalid file format", category="error")

    flash("Images uploaded successfully", category="success")
    return redirect(url_for("views.project", tab=IMAGE_TAB))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'bmp'}


@views.route("/delete_image/")
def delete_image():
    image_id = request.args.get("image_id", type=int)
    image_to_delete = Image.query.filter_by(id=image_id).first()
    if image_to_delete:
        db.session.delete(image_to_delete)
        db.session.commit()
        flash("Image successfully deleted", category="success")
    return redirect(url_for("views.project", tab=3))


@views.route("/run", methods=["POST"])
async def run(project_id):
    model = YOLO(MlModels.query.first().model)
    images_to_run = Image.query.filter_by(project_id=session["project_id"])
    n_images = images_to_run.count()
    if not n_images:
        flash("No images to run model", category="error")
        return redirect(url_for("views.project", project_id=session["project_id"]))
    step = 100 / n_images
    progress = 0
    for image in images_to_run:
        image_byte = image.image
        img_pil = PILImage.open(BytesIO(image_byte))
        img_np = np.array(img_pil)
        prediction = model.predict(img_np, stream=False, save=False, verbose=False)
        progress += step
        socket.emit("update progress", int(math.ceil(progress)))
        new_stats = Stats(image_id=image.id)
        db.session.add(new_stats)
        db.session.commit()
        pill_result = PILImage.fromarray(prediction[0].plot()[..., ::-1])
        classes = prediction[0].names
        results_classes = prediction[0].boxes.cls
        for class_id in results_classes:
            class_name = "_".join(classes[int(class_id)].lower().split(" "))
            setattr(new_stats, class_name, getattr(new_stats, class_name) + 1)
            db.session.commit()
        buff = BytesIO()
        pill_result.save(buff, format="PNG")
        buff.seek(0)
        encoded = base64.b64encode(buff.read()).decode("utf-8")
        image_bytes = base64.b64decode(encoded)
        image.annotated_image = image_bytes
        db.session.commit()
    flash("Model successfully run", category="success")
    db.session.close()
    return redirect(url_for("views.project_page", project_id=session["project_id"]))


@views.route("/delete_project/<int:project_id>")
def delete_project(project_id):
    project_to_delete = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if project_to_delete:
        db.session.delete(project_to_delete)
        db.session.commit()
        flash("Project successfully deleted", category="success")
    return redirect(url_for("views.home"))


@views.route("/show_image/<int:image_id>")
def show_image(image_id):
    img = Image.query.filter_by(id=image_id).first()
    file_type = img.name.split(".")[-1]
    return Response(img.image, mimetype=file_type)


@views.route("/show_image_annotated/<int:image_id>")
def show_image_annotated(image_id):
    img = Image.query.filter_by(id=image_id).first()
    file_type = img.name.split(".")[-1]
    return Response(img.annotated_image, mimetype=file_type)
