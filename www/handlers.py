#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import html
import json
import logging
import re
import time

from aiohttp import web

from www import markdown2
from www.apis import APIValueError, APIError, APIPermissionError, Page, APIResourceNotFoundError
from www.config import configs
from www.coroweb import get, post
from www.models import Blog, User, next_id, Comment

COOKIE_NAME = "awesome+session"

_COOKIE_KEY = configs.session.secret


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page: str):
    try:
        return max(int(page), 1)
    except ValueError:
        return 1


def user2cookie(user: User, max_age):
    expires = str(int(time.time() + max_age))
    s = "-".join([user.id, user.password, expires, _COOKIE_KEY])
    return "-".join([user.id, expires, hashlib.sha1(s.encode()).hexdigest()])


def text2html(text: str):
    return "\n".join("<p>{}</p>".format(html.escape(s))
                     for s in text.split("\n") if s.strip())


async def cookie2user(cookie: str):
    if not cookie:
        return None
    try:
        l = cookie.split("-")
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
async def index(*, page="1"):
    page_index = get_page_index(page)
    num = await Blog.find_number("count(id)")
    page = Page(num, page_index)
    blogs = [] if num == 0 else await Blog.find_all(orderBy="created_at desc", limit=(page.offset, page.limit))
    return {
        "__template__": "blogs.html",
        "blogs":        blogs,
        "page":         page
    }


@get("/blog/{id}")
async def get_blog(id):
    blog = await Blog.find(id)
    blog.user = await User.find(blog.user_id)
    blog.user.shadow_password()
    comments = await Comment.find_all("blog_id=?", [id], orderBy="created_at desc")
    for comment in comments:
        comment.html_content = text2html(comment.content)
        comment.user = await User.find(comment.user_id)
        comment.user.shadow_password()
    blog.html_content = markdown2.markdown(blog.content)
    return {
        "__template__": "blog.html",
        "blog":         blog,
        "comments":     comments
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


@get("/signout")
def signout(request):
    referer = request.headers.get("Referer")
    response = web.HTTPFound(referer or "/")
    response.set_cookie(COOKIE_NAME, "-deleted-", max_age=0, httponly=True)
    logging.info("user signed out.")
    return response


@get("/manage")
def manage():
    return "redirect:/manage/comments"


@get("/manage/comments")
def manage_comments(*, page="1"):
    return {
        "__template__": "manage_comments.html",
        "page_index":   get_page_index(page)
    }


@get("/manage/blogs")
def manage_blogs(*, page="1"):
    return {
        "__template__": "manage_blogs.html",
        "page_index":   get_page_index(page)
    }


@get("/manage/blogs/create")
def manage_create_blog():
    return {
        "__template__": "manage_blog_edit.html",
        "id":           "",
        "action":       "/api/blogs"
    }


@get("/manage/blogs/edit")
def manage_edit_blog(*, id):
    return {
        "__template__": "manage_blog_edit.html",
        "id":           id,
        "action":       "/api/blogs/{}".format(id)
    }


@get("/manage/users")
def manage_users(*, page="1"):
    return {
        "__template__": "manage_users.html",
        "page_index":   get_page_index(page)
    }


@get("/api/comments")
async def api_comments(*, page="1"):
    page_index = get_page_index(page)
    num = await Comment.find_number("count(id)")
    p = Page(num, page_index)
    if num == 0:
        comments = ()
    else:
        comments = await Comment.find_all(orderBy="created_at desc", limit=(p.offset, p.limit))
        for comment in comments:
            comment.user = await User.find(comment.user_id)
            comment.user.shadow_password()
    return {
        "page":     p,
        "comments": comments
    }


@post("/api/blogs/{id}/comments")
async def api_create_comments(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError("Please signin first.")
    if not content or not content.strip():
        raise APIValueError("content")
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError("Blog")
    comment = Comment(blog_id=blog.id, user_id=user.id, content=content.strip())
    await comment.save_data()
    return comment


@post("/api/comments/{id}/delete")
async def api_delete_comments(id, request):
    check_admin(request)
    comment = await Comment.find(id)
    if comment is None:
        raise APIResourceNotFoundError("comment")
    await comment.remove_data()
    return {"id": id}


@get("/api/users")
async def api_get_users(*, page="1"):
    page_index = get_page_index(page)
    num = await User.find_number("count(id)")
    p = Page(num, page_index)
    if num == 0:
        users = ()
    else:
        users = await User.find_all(orderBy="created_at desc", limit=(p.offset, p.limit))
        for user in users:
            user.shadow_password()
    return {
        "page":  p,
        "users": users
    }


_RE_EMAIL = re.compile(r'^[a-z0-9.\-_]+@[a-z0-9\-_]+(\.[a-z0-9\-_]+){1,4}$')
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


@get("/api/blogs")
async def api_blogs(*, page="1"):
    page_index = get_page_index(page)
    page_count = await Blog.find_number("count(id)")
    page = Page(page_count, page_index)
    blogs = await Blog.find_all(orderBy="created_at desc", limit=(page.offset, page.limit)) if page_count != 0 else []
    for blog in blogs:
        user = await User.find(blog.user_id)
        user.password = '********'
        setattr(blog, "user", user)
    return {"page": page, "blogs": blogs}


@get("/api/blogs/{id}")
async def api_get_blog(*, id):
    return await Blog.find(id)


@post("/api/blogs")
async def api_create_blog(request, *, title, summary, content):
    check_admin(request)
    if not title or not title.strip():
        raise APIValueError('title', 'title cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, title=title.strip(), summary=summary.strip(), content=content.strip())
    await blog.save_data()
    return blog


@post("/api/blogs/{id}")
async def api_update_blog(id, request, *, title, summary, content):
    check_admin(request)
    if not title or not title.strip():
        raise APIValueError("title", "title cannot be empty.")
    if not summary or not summary.strip():
        raise APIValueError("summary", "summary cannot be empty.")
    if not content or not content.strip():
        raise APIValueError("content", "content cannot be empty.")
    blog = await Blog.find(id)
    blog.name = title.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update_data()
    return blog


@post("/api/blogs/{id}/delete")
async def api_delete_blog(request, *, id):
    check_admin(request)
    blog = await Blog.find(id)
    await blog.remove_data()
    return {"id": id}
