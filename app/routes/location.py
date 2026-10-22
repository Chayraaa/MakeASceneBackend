from flask import Blueprint, request, current_app

location = Blueprint("location", __name__)

@location.route("", methods=["GET"])
def get_locations():
    query = request.args.get("q")
    force_api = request.args.get("force_api")

    if force_api and force_api.lower() not in ('false', '0', 'no'):
        res = current_app.location_service.autocomplete_location(query, force_api=True)
    else:
        res = current_app.location_service.autocomplete_location(query)
    return res, 200
