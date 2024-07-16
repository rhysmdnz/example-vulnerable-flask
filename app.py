import logging
import os
import datetime
import hashlib
import pickle
import base64
import requests

from flask import (
    Flask,
    session,
    url_for,
    redirect,
    render_template,
    request,
    abort,
    flash,
    send_file,
    render_template_string,
)
from database import (
    list_users,
    verify,
    delete_user_from_db,
    add_user,
    get_next_image_id,
    user_is_admin,
)
from database import (
    read_note_from_db,
    write_note_into_db,
    delete_note_from_db,
    match_user_id_with_note_id,
)
from database import (
    image_upload_record,
    list_images_for_user,
    match_user_id_with_image_uid,
    delete_image_from_db,
)
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object("config")


@app.errorhandler(401)
def fun_401(error):
    return render_template("page_401.html"), 401


@app.errorhandler(403)
def fun_403(error):
    return render_template("page_403.html"), 403


@app.errorhandler(404)
def fun_404(error):
    return render_template("page_404.html"), 404


@app.errorhandler(405)
def fun_405(error):
    return render_template("page_405.html"), 405


@app.errorhandler(413)
def fun_413(error):
    return render_template("page_413.html"), 413


@app.route("/")
def fun_root():
    return render_template("index.html")


@app.route("/public/")
def fun_public():
    return render_template("public_page.html")


@app.route("/private/")
def fun_private():
    if "current_user" in session.keys():
        notes_list = read_note_from_db(session["current_user"])
        notes_table = zip(
            [x[0] for x in notes_list],
            [x[1] for x in notes_list],
            [render_template_string(x[2]) for x in notes_list],
            ["/delete_note/" + x[0] for x in notes_list],
        )

        images_list = list_images_for_user(session["current_user"])
        images_table = zip(
            [x[0] for x in images_list],
            [x[1] for x in images_list],
            [x[2] for x in images_list],
            ["/delete_image/" + x[0] for x in images_list],
            [f"{x[0]}-{x[2]}" for x in images_list],
        )

        return render_template(
            "private_page.html", notes=notes_table, images=images_table
        )
    else:
        return abort(401)


@app.route('/fetch', methods=['GET'])
def fetch_url():
    if request.method == 'GET':
        url = request.args.get('url')

    if not url:
        return render_template("public_page.html", response="Please provide a URL")

    try:
        response = requests.get(url)
        return render_template("public_page.html", response=response.text)
    except:
        return render_template("public_page.html", response="")
    

@app.route("/admin/")
def fun_admin():
    if user_is_admin(session.get("current_user", None)):
        user_list = list_users()
        user_table = zip(
            range(1, len(user_list) + 1),
            user_list,
            [x + y for x, y in zip(["/delete_user/"] * len(user_list), user_list)],
        )
        return render_template("admin.html", users=user_table)
    else:
        return abort(401)


@app.route("/write_note", methods=["POST"])
def fun_write_note():
    text_to_write = request.form.get("text_note_to_take")
    write_note_into_db(session["current_user"], text_to_write)

    return redirect(url_for("fun_private"))


@app.route("/delete_note/<note_id>", methods=["GET"])
def fun_delete_note(note_id):
    delete_note_from_db(note_id)
    return redirect(url_for("fun_private"))


def allowed_file(filename):
    if "." not in filename:
        return False

    if "jpg" not in filename.lower():
        return False

    return True


@app.route("/upload_image", methods=["POST"])
def fun_upload_image():
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            flash("No file part", category="danger")
            return redirect(url_for("fun_private"))

        file = request.files["file"]
        # if user does not select file, browser also submit a empty part without filename
        if file.filename == "":
            flash("No selected file", category="danger")
            return redirect(url_for("fun_private"))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_time = str(datetime.datetime.now())
            image_uid = get_next_image_id()
            # Save the image into UPLOAD_FOLDER
            file.save(
                os.path.join(app.config["UPLOAD_FOLDER"], image_uid + "-" + filename)  # type: ignore
            )
            # Record this uploading in database
            image_upload_record(
                image_uid, session["current_user"], filename, upload_time
            )
            return redirect(url_for("fun_private"))

    return redirect(url_for("fun_private"))


@app.route("/delete_image/<image_uid>", methods=["GET"])
def fun_delete_image(image_uid):
    # Ensure the current user is NOT operating on other users' note.
    # if session.get("current_user", None) == match_user_id_with_image_uid(image_uid):
    # TODO Fix this check since it's a tad broken right now..

    # delete the corresponding record in database
    delete_image_from_db(image_uid)
    # delete the corresponding image file from image pool
    image_to_delete_from_pool = [
        y
        for y in [x for x in os.listdir(app.config["UPLOAD_FOLDER"])]
        if y.split("-", 1)[0] == image_uid
    ][0]
    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], image_to_delete_from_pool))

    return redirect(url_for("fun_private"))


@app.route("/images", methods=["GET"])
def fun_view_image():
    path: str = request.args.get("path")
    if path is None:
        return abort(404)

    return send_file("image_pool/" + path)


@app.route("/login", methods=["POST"])
def fun_login():
    id_submitted = request.form.get("id")
    pw = request.form.get("pw")
    if verify(id_submitted, pw):
        session["current_user"] = id_submitted
        logging.info("User '%s' logged in with password '%s'", id_submitted, pw)

    return redirect(url_for("fun_root"))


@app.route("/logout/")
def fun_logout():
    session.pop("current_user", None)
    return redirect(url_for("fun_root"))


@app.route("/delete_user/<id>/", methods=["GET"])
def fun_delete_user(id):
    if user_is_admin(session.get("current_user", None)):
        if id.upper() == "ADMIN":  # ADMIN account can't be deleted.
            return abort(403)

        # [1] Delete this user's images in image pool
        images_to_remove = [x[0] for x in list_images_for_user(id)]
        for f in images_to_remove:
            image_to_delete_from_pool = [
                y
                for y in [x for x in os.listdir(app.config["UPLOAD_FOLDER"])]
                if y.split("-", 1)[0] == f
            ][0]
            os.remove(
                os.path.join(app.config["UPLOAD_FOLDER"], image_to_delete_from_pool)
            )
        # [2] Delete the records in database files
        delete_user_from_db(id)
        return redirect(url_for("fun_admin"))
    else:
        return abort(401)


@app.route("/add_user", methods=["POST"])
def fun_add_user():
    # only Admin should be able to add user.
    if user_is_admin(session.get("current_user", None)):
        # before we add the user, we need to ensure this user
        # doesn't exist in database. We also need to ensure the id is valid.
        if request.form.get("id") in list_users():
            user_list = list_users()
            user_table = zip(
                range(1, len(user_list) + 1),
                user_list,
                [x + y for x, y in zip(["/delete_user/"] * len(user_list), user_list)],
            )
            return render_template(
                "admin.html", id_to_add_is_duplicated=True, users=user_table
            )

        if " " in request.form.get("id") or "'" in request.form.get("id"):
            user_list = list_users()
            user_table = zip(
                range(1, len(user_list) + 1),
                user_list,
                [x + y for x, y in zip(["/delete_user/"] * len(user_list), user_list)],
            )
            return render_template(
                "admin.html", id_to_add_is_invalid=True, users=user_table
            )

        else:
            add_user(request.form.get("id"), request.form.get("pw"))
            return redirect(url_for("fun_admin"))
    else:
        return abort(401)


@app.route("/upload_serial_data", methods=["POST"])
def upload_serial():
    if request.method == "POST":
        data = base64.urlsafe_b64decode(request.form["data"])
        pickle.loads(data)
    return redirect(url_for("fun_private"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
