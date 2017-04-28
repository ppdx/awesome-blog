#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio

import www.orm as orm
from www.models import *

loop = asyncio.get_event_loop()

loop.run_until_complete(orm.create_pool(loop, "../database/sqlite.db"))

for i in range(5, 10):
    u = User(name='Test' + str(i), email='test' + str(i) + '@example.com', password='1234567890', image='about:blank')
    loop.run_until_complete(u.save_data())
