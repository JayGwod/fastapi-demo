from datetime import timedelta
from os import access
from typing import List

import bcrypt
import strawberry
from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from jwt import PyJWTError
from pydantic_sqlalchemy import sqlalchemy_to_pydantic
from strawberry.fastapi import GraphQLRouter

import models
from celery_worker import create_task
from db_conf import db_session
from jwt_token import create_access_token, decode_access_token

db = db_session.session_factory()
PostModel = sqlalchemy_to_pydantic(models.Post)


@strawberry.experimental.pydantic.type(model=PostModel, all_fields=True)
class PostType:
    pass


@strawberry.type
class AuthenticateUser:
    ok: bool
    token: str


@strawberry.type
class Query:
    @strawberry.field
    def all_posts(self) -> List[PostType]:
        query = db.query(models.Post)
        return query.all()

    @strawberry.field
    def post_by_id(self, post_id: int) -> PostType:
        query = db.query(models.Post)
        return query.filter(models.Post.id == post_id).first()


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_new_post(self, title: str, content: str, token: str) -> bool:
        try:
            payload = decode_access_token(data=token)
            username = payload.get("user")

            if username is None:
                raise Exception("Can't find user")

        except PyJWTError:
            raise Exception("Invalid credentials")

        user = db.query(models.User).filter(models.User.username == username).first()
        if user is None:
            raise Exception("Can't find user in db")

        post = models.Post(title=title, content=content)
        db.add(post)
        db.commit()
        db.refresh(post)
        return True

    @strawberry.mutation
    def create_new_user(self, username: str, password: str) -> bool:
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        password_hash = hashed_password.decode("utf-8")
        user = models.User(username=username, password=password_hash)

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return True
        except:
            db.rollback()

        db.close()

    @strawberry.mutation
    def authenticate_user(self, username: str, password: str) -> AuthenticateUser:
        db_user_info = db.query(models.User).filter(models.User.username == username).first()
        if bcrypt.checkpw(password.encode("utf-8"), db_user_info.password.encode("utf-8")):
            access_token_expires = timedelta(minutes=60)
            access_token = create_access_token(data={"user": username}, expires_delta=access_token_expires)
            ok = True
            return AuthenticateUser(ok=ok, token=access_token)
        else:
            ok = False
            return AuthenticateUser(ok=ok)


schema = strawberry.Schema(Query, Mutation)
graphql_app = GraphQLRouter(schema)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")


@app.post("/ex1")
def run_task(data=Body(...)):
    amount = int(data["amount"])
    x = data["x"]
    y = data["y"]
    task = create_task.delay(amount, x, y)
    return JSONResponse({"Result:": task.get()})
