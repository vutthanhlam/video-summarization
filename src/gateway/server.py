import os, gridfs, pika, json, datetime
from flask import Flask, request
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util

server = Flask(__name__)
server.config["MONGO_VIDEO_URI"] = os.environ.get("MONGO_VIDEO_URI")
# connect the server with mongoDB
mongo = PyMongo(server)

# gridfs divides a big file into chunks of size <= 255kb
fs = gridfs.GridFS(mongo.db)

# connect gateway server with rabbitmq
connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
channel = connection.channel()

@server.route("/login", methods=["POST"])
def login():
    token, err = access.login(request)

    if not err:
        return token
    else:
        return err

@server.route("/upload", methods=["POST"])
def upload():
    access, err = validate.token(request)

    if err:
        return err
    
    access = json.loads(access)
    if access["exp"] <= datetime.datetime.utcnow() or not access["admin"]:
        return "not authorized", 401

    if len(request.files) > 1 or len(request.files) < 1:
        return "Exactly 1 file required", 400
    
    for _, f in request.files.items():
        err = util.upload(f, fs, channel, access)

        if err:
            return err
    
    return "success!", 200

@server.route("/download", methods=["GET"])
def download():
    access, err = validate.token(request)

    if err:
        return err
    
    access = json.loads(access)
    if access["exp"] <= datetime.datetime.utcnow() or not access["admin"]:
        return "not authorized", 401
    
    pass

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8080)