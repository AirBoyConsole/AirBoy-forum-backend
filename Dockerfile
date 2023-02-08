# syntax=docker/dockerfile:1

FROM python:3-alpine3.16

WORKDIR /python-docker
RUN adduser -D api

VOLUME ["/python-docker/api", "/python-docker/files"]

RUN echo "http://mirror.reenigne.net/alpine/edge/main" >> /etc/apk/repositories
RUN apk update && \
    apk upgrade
RUN apk add mariadb-connector-c-dev=3.3.3-r0 --repository=http://mirror.reenigne.net/alpine/edge/testing
RUN apk add gcc musl-dev

COPY requirements.txt requirements.txt
RUN pip3 install packaging
RUN pip3 install -r requirements.txt

RUN mkdir -p /python-docker/backup
RUN chown -R api:api /python-docker

USER api

EXPOSE 8080

CMD [ "python3", "/python-docker/api/api.py"]
