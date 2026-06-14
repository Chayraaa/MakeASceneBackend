from flask import Blueprint, request, current_app

from app import validate

tags = Blueprint("tags", __name__)


@tags.route("", methods=["GET"])
@validate
def get_tags():
    query = request.args.get("query")
    autocomplete = request.args.get("autocomplete")
    page = (request.args.get("page") or 0)
    if autocomplete:
        res = current_app.tag_service.autocomplete(query, page)
    else:
        res = current_app.tag_service.query_tags(query)

    formatted = [
        {
            "id": tag.id,
            "name": tag.name
        }
        for tag in res
    ]
    return {"tags": formatted}, 200


@tags.route("/<int:id>", methods=["GET"])
@validate
def get_tag_by_id(id: int):
    res = current_app.tag_service.get_tag(id)
    if res:
        return {
            "id": res.id,
            "name": res.name,
            "parent": res.parent
        }, 200
    return {
        "error": "Not Found",
        "message": "Tag was not found"
    }
