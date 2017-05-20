#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import uuid

from www.orm import Model, StringField, BooleanField, FloatField, TextField


def next_id() -> str:
    return "%018d%s" % (int(time.time() * 1000000), uuid.uuid4().hex)


class User(Model):
    __table__ = "users"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    email = StringField(ddl="varchar(50)")
    password = StringField(ddl="varchar(50)")
    admin = BooleanField()
    name = StringField(ddl="varchar(50)")
    image = StringField(ddl="varchar(500)")
    created_at = FloatField(default=time.time)

    def shadow_password(self):
        self.password = "********"


class Blog(Model):
    __table__ = "blogs"

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    title = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)


class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    content = TextField()
    created_at = FloatField(default=time.time)
