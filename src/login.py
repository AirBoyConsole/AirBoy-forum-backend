import hashlib
import datetime
from flask_restful import Resource, reqparse, abort
from flask_jwt_extended import create_access_token

from sql import execsql


class Login(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', location='form', required=True)
        parser.add_argument('password', location='form', required=True)
        args = parser.parse_args()

        result = execsql("select id,salt,hash from users where username like %s", (args["username"],))
        if result == []:
            abort(404, message="User with this username does not exist: {}".format(args["username"]))

        hash = hashlib.sha512((result[0][1] + args["password"]).encode()).hexdigest()
        if str(hash) != str(result[0][2]):
            print(hash + ", " + result[0][2])
            abort(401, message="Incorrect password")

        expires = datetime.timedelta(days=14)
        token = create_access_token(identity=str(result[0][0]), expires_delta=expires)
        return {"token": token}
