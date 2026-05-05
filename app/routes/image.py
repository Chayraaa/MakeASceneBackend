from flask import Blueprint, current_app, Response

from app import validate

image = Blueprint("image", __name__)

@image.route("/<path:key>", methods=["GET"])
@validate
def get_image(key):
    response = current_app.image_service.get_image_stream(key)

    return Response(
        response,
        mimetype="image/jpeg"
    )