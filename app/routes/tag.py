from flask import Blueprint, request, current_app

from app import validate

tags = Blueprint("tags", __name__)


@tags.route("", methods=["GET"])
@validate
def get_tags():
    query = request.args.get("query")
    res = current_app.tag_service.query_tags(query)

    formatted = [
        {
            "id": tag.id,
            "name": tag.name
        }
        for tag in res
    ]
    return {"tags": formatted}, 200
