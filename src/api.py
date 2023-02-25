from flask import Flask, request
from flask_restful import Api, Resource
from flask_jwt_extended import JWTManager
from waitress import serve

from article import Articles, Article, ArticlesByToken
from user import Users, User, UserByToken
from login import Login
from files import Files

app = Flask(__name__)
api = Api(app)

jwt = JWTManager(app)


@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE'
    return response


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


api.add_resource(Articles, '/api/article')
api.add_resource(Article, '/api/article/<article_id>')
api.add_resource(Users, '/api/user')
api.add_resource(User, '/api/user/<user_id>')
api.add_resource(UserByToken, '/api/self/')
api.add_resource(ArticlesByToken, '/api/self/article')
api.add_resource(Files, '/api/files/<file_id>')
api.add_resource(Login, '/api/login')

app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024
app.config['JWT_SECRET_KEY'] = \
    '2b946a808437ed7f2ea10e309168bf1618ed6228111094e22a0316e9cced530e'
app.config['PROPAGATE_EXCEPTIONS'] = True

if __name__ == '__main__':
    # app.run('127.0.0.1', debug=True, port=8080)
    serve(app, host='0.0.0.0', port=8080, threads=12)
