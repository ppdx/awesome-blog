#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import re
import time

from aiohttp import web

from www.apis import APIValueError, APIError
from www.config import configs
from www.coroweb import get, post
from www.models import Blog, User, next_id

COOKIE_NAME = "awesome+session"

_COOKIE_KEY = configs.session.secret


def user2cookie(user: User, max_age):
    expires = str(int(time.time() + max_age))
    s = "-".join([user.id, user.password, expires, _COOKIE_KEY])
    return "-".join([user.id, expires, hashlib.sha1(s.encode()).hexdigest()])


async def cookie2user(cookie_str: str):
    if not cookie_str:
        return None
    try:
        l = cookie_str.split("-")
        if len(l) != 3:
            return None
        uid, expires, sha1 = l
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = "-".join([uid, user.password, expires, _COOKIE_KEY])
        if sha1 != hashlib.sha1(s.encode()).hexdigest():
            logging.info("invalid sha1")
            return None
        user.password = "********"
        return user
    except Exception as e:
        logging.exception(e)
        return None


@get("/")
def index(request):
    summary = "don't panic, c'est la vie."
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time() - 120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time() - 7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs':        blogs
    }


@get("/register")
def register():
    return {
        "__template__": "register.html"
    }


@get("/login")
def login():
    return {
        "__template__": "login.html"
    }


@post("/api/authenticate")
async def authenticate(*, email, password):
    if not email:
        raise APIValueError("email", "email is None")
    if not password:
        raise APIValueError("password", "password is None")
    users = await User.find_all("email=?", [email])
    if len(users) == 0:
        raise APIValueError("email", "email not exist")
    user = users[0]

    # check password
    sha1 = hashlib.sha1(user.id.encode() + b":" + password.encode())
    if user.password != sha1.hexdigest():
        raise APIValueError("password", "invalid password")

    # authenticate ok, set cookie
    response = web.Response()
    response.set_cookie(COOKIE_NAME, user2cookie(user, 86400))
    user.password = "********"
    response.content_type = "application/json"
    response.body = json.dumps(user, ensure_ascii=False).encode()
    return response


_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


@post("/api/register")
async def api_register_user(*, email, name, password):
    if not name or not name.strip():
        raise APIValueError("name")
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError("email")
    if not password or not _RE_SHA1.match(password):
        raise APIValueError("password")
    users = await User.find_all("email=?", [email])
    if len(users) != 0:
        raise APIError("register:failed", "email", "email is already in use.")
    uid = next_id()
    sha1_password = (uid + ":" + password).encode()
    user = User(id=uid,
                name=name.strip(),
                email=email,
                password=hashlib.sha1(sha1_password).hexdigest(),
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest()
                )
    await user.save_data()

    # make session cookie:
    response = web.Response()
    response.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '********'
    response.content_type = 'application/json'
    response.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return response
