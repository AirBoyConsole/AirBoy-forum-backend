import os
import datetime
import uuid
from flask import url_for
from flask_restful import Resource, reqparse, abort
from werkzeug.datastructures import FileStorage
from flask_jwt_extended import jwt_required, get_jwt_identity

from sql import execsql
from mongo import articles
from config import ALLOWED_EXTENSIONS, IMAGE_ALLOWED_EXTENSIONS, UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_image(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in IMAGE_ALLOWED_EXTENSIONS


class Articles(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('offset', type=int, location='args', default=0)
        parser.add_argument('limit', type=int, location='args', default=20)
        parser.add_argument('sort_by', location='args', default='DATE', choices=('NAME', 'ID', 'DATE', 'VIEWS'))
        parser.add_argument('order', type=int, location='args', default=0, choices=(0, 1))
        parser.add_argument('search', location='args', default='')
        args = parser.parse_args()


        sortenum = {'NAME': 'title',
                    'ID': 'id',
                    'DATE': 'added',
                    'VIEWS': 'views'}
        orderenum = [1, -1]
        # searchdict = {'$text': {'$search': '/'+args["search"]+'/'}}
        # searchdict = {'title': {'$regex': args["search"]}, 'title': {'$regex': args["search"]}}
        searchdict = {'$or': [{'title': {'$regex': args["search"]}}, {'content': {'$regex': args["search"]}}]}

        result = articles.find(searchdict).sort(sortenum[args["sort_by"]],orderenum[args["order"]]).skip(int(args['offset'])).limit(int(args['limit']))
        json = []

        for entry in result:
            sql_result = execsql("select id,username,privileges from users where id="+str(entry["author"]))
            if len(sql_result) > 0:
                author_id = sql_result[0][0]
                author_username = sql_result[0][1]
                author_privileges = sql_result[0][2]
            else:
                author_id = 0
                author_username = "<deleted>"
                author_privileges = "regular"

            json.append({
                "id": entry["_id"],
                "title": entry["title"],
                "content": entry["content"],
                "download_url": entry["download_url"],
                "image_url": entry["image_url"],
                "added": entry["added"].isoformat(),
                "last_edit": entry["last_edit"].isoformat(),
                "author": {
                    "id": author_id,
                    "username": author_username,
                    "privileges": author_privileges
                },
                "tags": entry["tags"],
                "views": entry["views"],
            })

        return json


    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('title', location='form', required=True)
        parser.add_argument('content', location='form', required=True)
        # parser.add_argument('author', location='form', required=True)
        parser.add_argument('file', type=FileStorage, location='files', required=False)
        parser.add_argument('image', type=FileStorage, location='files', required=True)
        parser.add_argument('tags', location='form', action='append')
        args = parser.parse_args()

        user_id = int(get_jwt_identity())
        sql_result = execsql("select id from users where id = %d", (user_id,))
        if sql_result == []:
            abort(400, message="The user of this token does not exist")

        if len(args["title"]) < 3:
            abort(400, message="Title should be at least 3 characters long: {}".format(args["title"]))

        if len(args["content"]) < 10:
            abort(400, message="Content should be at least 10 characters long: {}".format(args["content"]))

        file = args["file"]
        file_url = ''

        #if file.filename == '':
        #    abort(400, message="No file attached")

        #if file.filename != '':
        if file:
            if allowed_file(file.filename):
                while True:
                    try:
                        filename = uuid.uuid4().hex +"."+ file.filename.rsplit('.', 1)[1].lower()
                        file.save(os.path.join(UPLOAD_FOLDER, filename))
                        break
                    except:
                        pass
                file_url = url_for('files', file_id=filename)
            else:
                abort(400, message="File extension not allowed: {}".format(file.filename.rsplit('.', 1)[1].lower()))

        image = args["image"]

        if not image:
            abort(400, message="No image attached")

        if image and allowed_image(image.filename):
            while True:
                try:
                    filename = uuid.uuid4().hex +"."+ image.filename.rsplit('.', 1)[1].lower()
                    image.save(os.path.join(UPLOAD_FOLDER, filename))
                    break
                except:
                    pass
            image_url = url_for('files', file_id=filename)
        else:
            abort(400, message="Image extension not allowed: {}".format(image.filename.rsplit('.', 1)[1].lower()))

        date = datetime.datetime.utcnow()

        if articles.count_documents({}) != 0:
            id = int(articles.find({},{"_id": 1}).sort("_id", -1).limit(1)[0]["_id"]) + 1
        else:
            id = 0

        json = {
            '_id': id,
            'title': args['title'],
            'content': args['content'],
            'download_url': file_url,
            'image_url': image_url,
            'added': date,
            'last_edit': date,
            'author': user_id,
            #'tags': args['tags'].split(","),
            'tags': args['tags'],
            'views': 0
        }

        articles.insert_one(json)


class Article(Resource):
    def get(self, article_id):
        if articles.count_documents({"_id": int(article_id)}) == 0:
            abort(404, message="Article with this ID does not exist: {}".format(article_id))

        entry = articles.find({"_id": int(article_id)})[0];

        sql_result = execsql("select id,username from users where id="+str(entry["author"]))
        author_id = sql_result[0][0]
        author_username = sql_result[0][1]

        json = {
            "id": str(entry["_id"]),
            "title": entry["title"],
            "content": entry["content"],
            "download_url": entry["download_url"],
            "image_url": entry["image_url"],
            "added": entry["added"].isoformat(),
            "last_edit": entry["last_edit"].isoformat(),
            "author": {
                "id": author_id,
                "username": author_username
            },
            "tags": entry["tags"],
            "views": entry["views"],
        }

        articles.update_one({"_id": int(article_id)}, {"$set": {"views": int(entry["views"]) + 1}})

        return json


    @jwt_required()
    def delete(self, article_id):
        if articles.count_documents({"_id": int(article_id)}) == 0:
            abort(404, message="Article with this ID does not exist: {}".format(article_id))

        entry = articles.find({"_id": int(article_id)})[0];

        user_id = int(get_jwt_identity())

        result = execsql("select privileges+0 from users where id=%d", (user_id,))[0]
        if result == []:
            abort(400, message="The user of this token does not exist")

        sqlresult = execsql("select privileges+0 from users where id=%d", (entry["author"],))[0]
        if sqlresult == []:
            authorpriv = 1
        else:
            authorpriv = sqlresult[0]

        if user_id != int(entry["author"]) and int(result[0]) <= int(authorpriv):
            abort(403, message="You do not have privilege for this action")

        file = os.path.basename(entry['download_url'])

        try:
            os.remove(os.path.join(UPLOAD_FOLDER, file))
        except:
            pass

        image = os.path.basename(entry['image_url'])

        try:
            os.remove(os.path.join(UPLOAD_FOLDER, image))
        except:
            pass

        articles.delete_one({"_id": int(article_id)})


    @jwt_required()
    def put(self, article_id):
        parser = reqparse.RequestParser()
        parser.add_argument('title', location='form')
        parser.add_argument('content', location='form')
        parser.add_argument('file', type=FileStorage, location='files')
        parser.add_argument('image', type=FileStorage, location='files')
        parser.add_argument('tags', location='form', action='append')
        args = parser.parse_args()

        if articles.count_documents({"_id": int(article_id)}) == 0:
            abort(404, message="Article with this ID does not exist: {}".format(article_id))

        entry = articles.find({"_id": int(article_id)})[0]

        user_id = int(get_jwt_identity())

        result = execsql("select privileges+0 from users where id=%d", (user_id,))[0]
        if result == []:
            abort(400, message="The user of this token does not exist")

        sqlresult = execsql("select privileges+0 from users where id=%d", (entry["author"],))[0]
        if sqlresult == []:
            authorpriv = 1
        else:
            authorpriv = sqlresult[0]

        if user_id != int(entry["author"]) and int(result[0]) <= int(authorpriv):
            #print("user_id: "+str(user_id))
            #print("author: "+str(entry["author"]))
            #print("priv: "+str(result[0]))
            #print("authorpriv: "+str(authorpriv))
            abort(403, message="You do not have privilege for this action")

        newvals = {'last_edit': datetime.datetime.utcnow()}

        if args["title"] is not None:
            if len(args["title"]) < 3:
                abort(400, message="Title should be at least 3 characters long: {}".format(args["title"]))
            else:
                newvals["title"] = args["title"]

        if args["content"] is not None:
            if len(args["content"]) < 10:
                abort(400, message="Title should be at least 10 characters long: {}".format(args["content"]))
            else:
                newvals["content"] = args["content"]

        if args["tags"] is not None:
            newvals["tags"] = args["tags"].split(",")

        file = args["file"]

        if file is not None and file.filename != '':
            if file and allowed_file(file.filename):
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, os.path.basename(articles.find({"_id": int(article_id)})[0]['download_url'])))
                except:
                    pass
                filename = uuid.uuid4().hex +"."+ file.filename.rsplit('.', 1)[1].lower()
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                file_url = url_for('files', file_id=filename)
                newvals["download_url"] = file_url
            else:
                abort(400, message="File extension not allowed: {}".format(file.filename.rsplit('.', 1)[1].lower()))

        image = args["image"]

        if image is not None and image.filename != '':
            if image and allowed_image(image.filename):
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, os.path.basename(articles.find({"_id": int(article_id)})[0]['image_url'])))
                except:
                    pass
                filename = uuid.uuid4().hex +"."+ image.filename.rsplit('.', 1)[1].lower()
                image.save(os.path.join(UPLOAD_FOLDER, filename))
                image_url = url_for('files', file_id=filename)
                newvals["image_url"] = image_url
            else:
                abort(400, message="Image extension not allowed: {}".format(image.filename.rsplit('.', 1)[1].lower()))

        articles.update_one({"_id": int(article_id)}, {"$set": newvals})


class ArticlesByToken(Resource):
    @jwt_required()
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('offset', type=int, location='args', default=0)
        parser.add_argument('limit', type=int, location='args', default=20)
        parser.add_argument('sort_by', location='args', default='DATE', choices=('NAME', 'ID', 'DATE', 'VIEWS'))
        parser.add_argument('order', type=int, location='args', default=0, choices=(0, 1))
        parser.add_argument('search', location='args', default='')
        args = parser.parse_args()

        user_id = int(get_jwt_identity())

        result = execsql("select privileges+0 from users where id=%d", (user_id,))[0]
        if result == []:
            abort(400, message="The user of this token does not exist")

        sortenum = {'NAME': 'title',
                    'ID': 'id',
                    'DATE': 'added',
                    'VIEWS': 'views'}
        orderenum = [1, -1]
        # searchdict = {'$text': {'$search': '/'+args["search"]+'/'}}
        # searchdict = {'title': {'$regex': args["search"]}, 'title': {'$regex': args["search"]}}
        searchdict = {'$or': [{'title': {'$regex': args["search"]}}, {'content': {'$regex': args["search"]}}], 'author': user_id}
        # userdict = {'author': user_id}

        result = articles.find(searchdict).sort(sortenum[args["sort_by"]],orderenum[args["order"]]).skip(int(args['offset'])).limit(int(args['limit']))
        json = []

        for entry in result:
            sql_result = execsql("select id,username,privileges from users where id="+str(entry["author"]))
            if len(sql_result) > 0:
                author_id = sql_result[0][0]
                author_username = sql_result[0][1]
                author_privileges = sql_result[0][2]
            else:
                author_id = 0
                author_username = "<deleted>"
                author_privileges = "regular"

            json.append({
                "id": entry["_id"],
                "title": entry["title"],
                "content": entry["content"],
                "download_url": entry["download_url"],
                "image_url": entry["image_url"],
                "added": entry["added"].isoformat(),
                "last_edit": entry["last_edit"].isoformat(),
                "author": {
                    "id": author_id,
                    "username": author_username,
                    "privileges": author_privileges
                },
                "tags": entry["tags"],
                "views": entry["views"],
            })

        return json
