#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

from www.coroweb import get
from www.models import Blog, User


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


@get("/api/users")
async def api_get_users():
    users = await User.find_all(orderBy="created_at desc")
    for user in users:
        user.password = "********"
    return {"users": users}
