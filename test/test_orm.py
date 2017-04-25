#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio

import www.orm as orm
from www.models import *

loop = asyncio.get_event_loop()

loop.run_until_complete(orm.create_pool(loop, "../database/sqlite.db"))

u = User(name='Test', email='test@example.com', password='1234567890', image='about:blank')

loop.run_until_complete(u.save())
