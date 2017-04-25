#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import functools
import inspect
import logging
import os
from urllib.parse import parse_qs

from aiohttp import web

from www.apis import APIError


def get(path):
    """define decorator @get("/path")"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = "GET"
        wrapper.__route__ = path
        return wrapper

    return decorator


def post(path):
    """define decorator @post("/path")"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = "POST"
        wrapper.__route__ = path
        return wrapper

    return decorator


def get_required_kwargs(func):
    return tuple(name for name, param in inspect.signature(func).parameters.items()
                 if param.kind == inspect.Parameter.KEYWORD_ONLY and
                 param.default == inspect.Parameter.empty)


def get_named_kwargs(func):
    return tuple(name for name, param in inspect.signature(func).parameters.items()
                 if param.kind == inspect.Parameter.KEYWORD_ONLY)


def has_named_kwargs(func):
    return any(param.kind == inspect.Parameter.KEYWORD_ONLY
               for param in inspect.signature(func).parameters.values())


def has_var_kwarg(func):
    return any(param.kind == inspect.Parameter.VAR_KEYWORD
               for param in inspect.signature(func).parameters.values())


def has_request_arg(func):
    sig = inspect.signature(func)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == "request":
            found = True
            continue
        if found and param.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.KEYWORD_ONLY,
                inspect.Parameter.VAR_KEYWORD):
            raise ValueError(
                    "request parameter must be the last named parameter in function: {}{}".format(func.__name__, sig))
    return found


class RequestHandler:
    def __init__(self, app, func):
        self._app = app
        self._func = func
        self._has_request_arg = has_request_arg(func)
        self._has_var_kwarg = has_var_kwarg(func)
        self._has_named_kwargs = has_named_kwargs(func)
        self._named_kwargs = get_named_kwargs(func)
        self._required_kwargs = get_required_kwargs(func)

    async def __call__(self, request):
        kwargs = None
        if self._has_var_kwarg or self._has_named_kwargs or self._required_kwargs:
            if request.method == "POST":
                if not request.content_type:
                    return web.HTTPBadRequest("Missing Content-Type.")
                content = request.content_type.lower()
                if content.startswith("application/json"):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest("JSON body must be object.")
                    kwargs = params
                elif content.startswith('application/x-www-form-urlencoded') or \
                        content.startswith('multipart/form-data'):
                    params = await request.post()
                    kwargs = dict(**params)
                else:
                    return web.HTTPBadRequest("Unsupported Content-Type: " + request.content_type)
            elif request.method == "GET":
                query_string = request.query_string
                if query_string:
                    kwargs = {k: v[0] for k, v in parse_qs(query_string, True).items()}
        if kwargs is None:
            kwargs = dict(**request.match_info)
        else:
            if not self._has_var_kwarg and self._named_kwargs:
                # remove all unnamed kwarg
                kwargs = {name: kwargs[name] for name in self._named_kwargs if name in kwargs}
            for k, v in request.match_info.items():
                if k in kwargs:
                    logging.warning("Duplicate arg name in named arg and kwargs: " + k)
                kwargs[k] = v
        if self._has_request_arg:
            kwargs["request"] = request

        # check required kwarg
        if self._required_kwargs:
            for name in self._required_kwargs:
                if name not in kwargs:
                    return web.HTTPBadRequest("Missing argument: " + name)
        logging.info("call with args: {}" + str(kwargs))
        try:
            return await self._func(**kwargs)
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    app.router.add_static("/static/", path)
    logging.info("add static {} => {}".format("/static/", path))


def add_route(app, func):
    method = getattr(func, "__method__", None)
    path = getattr(func, "__route__", None)
    if path is None or method is None:
        raise ValueError("@get or @post not define in {}.".format(func))
    if not asyncio.iscoroutinefunction(func) and not inspect.isgeneratorfunction(func):
        func = asyncio.coroutine(func)
    logging.info("add route {} {} => {}({})".format(
            method, path, func.__name__, ", ".join(inspect.signature(func).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, func))


def add_routes(app, module_name):
    n = module_name.rfind(".")
    if n == -1:
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n + 1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith("_"):
            continue
        func = getattr(mod, attr)
        if callable(func):
            method = getattr(func, "__method__", None)
            path = getattr(func, "__route__", None)
            if method and path:
                add_route(app, func)
