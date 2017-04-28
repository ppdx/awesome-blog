#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from www.coroweb import get
from www.models import User


@get("/")
async def index(request):
    users = await User.find_all()
    return {
        "__template__": "test.html",
        "users":        users
    }
