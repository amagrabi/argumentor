from flask import jsonify


def json_error(message, status_code):
    return jsonify({"error": message}), status_code
