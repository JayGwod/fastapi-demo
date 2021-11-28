# Tutorial

```shell
pip install fastapi uvicorn[standard] strawberry-graphql[fastapi] alembic psycopg2 black python-dotenv bcrypt PyJWT celery redis flower pytest requests mangum

alembic init alembic

docker-compose run app alembic revision --autogenerate -m "New Migration"
docker-compose run app alembic upgrade head

docker-compose build
docker-compose up
```
