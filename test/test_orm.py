#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging

import www.orm as orm
from www.models import *


async def insert():
    await orm.create_pool(loop, "../database/sqlite.db")
    for i in range(1, 5):
        u = User(id=str(i), name='Test' + str(i), email='test' + str(i) + '@example.com', password='1234567890',
                 image='about:blank')
        await u.save_data()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(insert())
