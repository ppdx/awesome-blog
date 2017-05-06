#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import os
import time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from www import orm
from www.coroweb import add_routes, add_static
from www.handlers import COOKIE_NAME, cookie2user

logging.basicConfig(level=logging.INFO)


def init_jinja2(app, **kwargs):
    logging.info('init jinja2...')
    options = {
        "autoescape":            kwargs.get("autoescape", True),
        "block_start_string":    kwargs.get("block_start_string", "{%"),
        "block_end_string":      kwargs.get("block_end_string", "%}"),
        "variable_start_string": kwargs.get("variable_start_string", "{{"),
        "auto_reload":           kwargs.get("auto_reload", True)
    }
    path = kwargs.get("path", None) or os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    logging.info("set jinja2 template path: %s", path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kwargs.get("filters", None)
    if filters is not None:
        for name, filter in filters.items():
            env.filters[name] = filter
    app["__templating__"] = env


async def logger_factory(app, handler):
    async def logger(request):
        logging.info("Request: %s %s", request.method, request.path)
        return await handler(request)

    return logger


async def auth_factory(app, handler):
    async def auth(request):
        logging.info("check user: %s %s", request.method, request.path)
        request.__user__ = None
        cookie = request.cookies.get(COOKIE_NAME)
        if cookie:
            user = await cookie2user(cookie)
            if user:
                logging.info("set current user: %s", user.email)
                request.__user__ = user
        if request.path.startswith("/manage/") and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound("/login")
        return await handler(request)

    return auth


async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == "POST":
            if request.content_type.startswith("application/json"):
                request.__data__ = await request.json()
                logging.info("request json: {}".format(request.__data__))
            elif request.content_type.startswith("application/x-www-form-urlencoded"):
                request.__data__ = await request.post()
                logging.info("request form: {}".format(request.__data__))
        return await handler(request)

    return parse_data


async def response_factory(app, handler):
    async def response(request):
        logging.info("Response handler...")
        resp = await handler(request)
        if isinstance(resp, web.StreamResponse):
            pass
        elif isinstance(resp, bytes):
            resp = web.Response(body=resp)
            resp.content_type = "application/octet-stream"
        elif isinstance(resp, str):
            if resp.startswith("redirect:"):
                return web.HTTPFound(resp[9:])
            resp = web.Response(body=resp.encode())
            resp.content_type = "text/html;charset=utf-8"
        elif isinstance(resp, dict):
            template = resp.get("__template__")
            if template is None:
                resp = web.Response(
                        body=json.dumps(resp, ensure_ascii=False, default=lambda obj: obj.__dict__).encode())
                resp.content_type = "application/json;charset=utf-8"
            else:
                resp["__user__"] = request.__user__
                resp = web.Response(body=app["__templating__"].get_template(template).render(**resp).encode())
                resp.content_type = "text/html;charset=utf-8"
        elif isinstance(resp, int) and 100 <= resp < 600:
            resp = web.Response(status=resp)
        elif isinstance(resp, tuple) and len(resp) == 2 and isinstance(resp[0], int) and 100 <= resp[0] < 600:
            resp = web.Response(status=resp[0], body=str(resp[1]))
        else:
            resp = web.Response(body=str(resp).encode())
            resp.content_type = "text/plain;charset=utf-8"
        return resp

    return response


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return "1分钟前"
    elif delta < 3600:
        return "{}分钟前".format(delta // 60)
    elif delta < 86400:
        return "{}小时前".format(delta // 3600)
    elif delta < 604800:
        return "{}天前".format(delta // 86400)
    else:
        return datetime.fromtimestamp(t).isoformat()


async def init():
    await orm.create_pool(loop, "../database/sqlite.db")
    app = web.Application(loop=loop, middlewares=[
        logger_factory, auth_factory, response_factory
    ])
    init_jinja2(app, filters={"datetime": datetime_filter})
    add_routes(app, "handlers")
    add_static(app)
    srv = await loop.create_server(app.make_handler(), "127.0.0.1", 9000)
    logging.info("server started at http://127.0.0.1:9000")
    return srv


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
    loop.run_forever()
