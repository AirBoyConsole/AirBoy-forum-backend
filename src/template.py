from flask import request
from flask_restful import Resource

class Test(Resource):
    def get(self):
        args = request.args
        return args

    def post(self):
        args = request.form
        return args

    def delete(self):
        args = request.args
        return args

    def put(self):
        args = request.form
        return args


