from flask_restful import Resource
from flask import send_from_directory

from config import UPLOAD_FOLDER


class Files(Resource):
    def get(self, file_id):
        return send_from_directory(UPLOAD_FOLDER, file_id)
