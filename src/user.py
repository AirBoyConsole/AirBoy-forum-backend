import secrets
import hashlib
from flask_restful import Resource, reqparse, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

from sql import execsql


class Users(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('offset', type=int, location='args', default=0)
        parser.add_argument('limit', type=int, location='args', default=20)
        parser.add_argument('sort_by', location='args', default='ID', choices=('NAME', 'ID'))
        parser.add_argument('order', type=int, location='args', default=0, choices=(0, 1))
        parser.add_argument('search', location='args', default='')
        args = parser.parse_args()

        sortenum = {'NAME': 'username', 'ID': 'id'}
        orderenum = ['asc', 'desc']

        query = "select id,username,email,privileges from users where username like %s order by "+sortenum[args["sort_by"]]+" "+orderenum[args["order"]]+" limit %s offset %s"
        result = execsql(query, ('%'+args["search"]+'%', args["limit"], args["offset"]))
        json = []

        for entry in result:
            json.append({
                "id": entry[0],
                "username": entry[1],
                "privileges": entry[3]
            })

        return json


    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', location='form', required=True)
        parser.add_argument('password', location='form', required=True)
        parser.add_argument('email', location='form', required=True)
        args = parser.parse_args()

        if len(args["username"]) < 3:
            abort(400, message="Username should be at least 3 characters long: {}".format(args["username"]))

        sql_result = execsql("select username from users where username like %s", (args["username"],))
        if sql_result != []:
            abort(400, message="Username already exists: {}".format(args["username"]))

        if len(args["password"]) < 8:
            abort(400, message="Password should be at least 8 characters long: {}".format(args["password"]))

        salt = secrets.token_hex(16)
        hash = hashlib.sha512((salt+args["password"]).encode()).hexdigest()

        execsql("insert into users values (NULL,%s,%s,%s,%s,%d)", (args['username'], salt, hash, args['email'], 1))


class User(Resource):
    def get(self, user_id):

        result = execsql("select id,username,email,privileges from users where id=%d", (int(user_id),))
        if result == [] or user_id == 0:
            abort(404, message="User with this ID does not exist: {}".format(user_id))

        json = {
            "id": result[0][0],
            "username": result[0][1],
            "privileges": result[0][3]
        }

        return json


    @jwt_required()
    def delete(self, user_id):

        result = execsql("select id,username,email,privileges+0 from users where id=%d", (int(user_id),))
        if result == [] or user_id == 0:
            abort(404, message="User with this ID does not exist: {}".format(user_id))

        token_user_id = int(get_jwt_identity())

        sqlresult = execsql("select privileges+0 from users where id=%d", (token_user_id,))[0]
        if sqlresult == []:
            abort(400, message="The user of this token does not exist")

        if user_id != token_user_id and int(sqlresult[0]) <= int(result[0][3]):
            abort(403, message="You do not have privilege for this action")

        execsql("delete from users where id=%s", (user_id,))

        return '', 204


    @jwt_required()
    def put(self, user_id):
        parser = reqparse.RequestParser()
        parser.add_argument('username', location='form')
        parser.add_argument('password', location='form')
        parser.add_argument('email', location='form')
        parser.add_argument('privileges', type=int, location='form', default=0, choices=(1,2,3))
        args = parser.parse_args()

        result = execsql("select id,username,salt,hash,email,privileges+0 from users where id=%d", (int(user_id),))
        if result == [] or user_id == 0:
            abort(404, message="User with this ID does not exist: {}".format(user_id))

        token_user_id = int(get_jwt_identity())

        sqlresult = execsql("select privileges+0 from users where id=%d", (token_user_id,))[0]
        if sqlresult == []:
            abort(400, message="The user of this token does not exist")

        if user_id != token_user_id and int(sqlresult[0]) <= int(result[0][3]):
            abort(403, message="You do not have privilege for this action")

        if int(args["privileges"]) != 0:
            if int(args["privileges"]) >= int(sqlresult[0]):
                abort(403, message="You cannot grant this level of privileges")
            privileges = int(args["privileges"])
        else:
            privileges = result[0][5]

        if user_id == token_user_id:
            if args["username"] is not None and len(args["username"]) > 0:
                if len(args["username"]) < 3:
                    abort(400, message="Username should be at least 3 characters long: {}".format(args["username"]))

                sql_result = execsql("select username from users where username like %s", (args["username"],))
                if sql_result != []:
                    abort(400, message="Username already exists: {}".format(args["username"]))

                username = args["username"]
            else:
                username = result[0][1]

            if args["password"] is not None and len(args["password"]) > 0:
                if len(args["password"]) < 8:
                    abort(400, message="Password should be at least 8 characters long: {}".format(args["password"]))

                salt = secrets.token_hex(16)
                hash = hashlib.sha512((salt+args["password"]).encode()).hexdigest()
            else:
                salt = result[0][2]
                hash = result[0][3]

            if args["email"] is not None and len(args["email"]) > 0:
                email = args["email"]
            else:
                email = result[0][4]

            execsql("update users set username=%s,salt=%s,hash=%s,email=%s,privileges=%d where id=%d", (username, salt, hash, email, privileges, user_id))
        else:
            execsql("update users set privileges=%d where id=%d", (privileges, user_id))
