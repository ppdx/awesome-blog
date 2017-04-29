#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

import aioodbc

_pool = None


def log(sql, args=()):
    logging.info("SQL: {} ARGS: {}".format(sql, args))


async def create_pool(loop, database: str):
    logging.info("create database connection pool...")
    global _pool
    # 需要安装SQLite ODBC驱动 http://www.ch-werner.de/sqliteodbc/
    _pool = await aioodbc.create_pool(dsn="DRIVER={SQLite3 ODBC Driver};Database=" + database, loop=loop)


async def select(sql, args, size=None):
    log(sql, args)
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args or ())
            ret = await (cur.fetchmany(size) if size else cur.fetchall())
            logging.info("rows returned: %d", len(ret))
    return ret


async def execute(sql, args):
    log(sql, args)
    async with _pool.acquire() as conn:
        # await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                affected = cur.rowcount
                await conn.commit()
        except:
            await conn.rollback()
            raise
    return affected


def create_args_string(num):
    return ", ".join(["?"] * num)


class Field:
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return "<{}, {}:{}>".format(self.__class__.__name__, self.column_type, self.name)

    __repr__ = __str__


class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl="varchar(100)"):
        super(StringField, self).__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super(BooleanField, self).__init__(name, "boolean", False, default)


class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super(IntegerField, self).__init__(name, "bigint", primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class StandardError(Exception):
    pass


class ModelMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        if name == "Model":
            return type.__new__(mcs, name, bases, attrs)
        table_name = attrs.get("__table__", None) or name
        logging.info("found model: %s (table: %s)", name, table_name)
        mappings = {}
        fields = []
        primary_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info("\tfound mapping: %s ==> %s", k, v)
                mappings[k] = v
                if v.primary_key:
                    if primary_key:
                        raise StandardError("Duplicate primary key for field: {}".format(k))
                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise StandardError("Primary key not found.")
        for k in mappings.keys():
            del attrs[k]
        escaped_fields = ",".join("`{}`".format(field) for field in fields)
        attrs["__mapping__"] = mappings
        attrs["__table__"] = table_name
        attrs["__primary_key__"] = primary_key
        attrs["__fields__"] = fields
        attrs["__select__"] = "select `{}`, {} from `{}`".format(primary_key, escaped_fields, table_name)
        attrs["__insert__"] = "insert into `{}` ({}, `{}`) values ({})".format(table_name, escaped_fields, primary_key,
                                                                               create_args_string(len(fields) + 1))
        attrs["__update__"] = "update `{}` set {} where `{}`=?".format(
                table_name, ', '.join(["`{}`=?".format(mappings.get(field).name or field) for field in fields]),
                primary_key)
        attrs["__delete__"] = "delete from `{}` where `{}`=?".format(table_name, primary_key)
        return type.__new__(mcs, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        super(ModelMetaclass, cls).__init__(name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kwargs):
        super(Model, self).__init__(**kwargs)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'Model' object has no attribute `{}`".format(key))

    def __setattr__(self, key, value):
        self[key] = value

    def get_value(self, key):
        return getattr(self, key, None)

    def get_value_or_default(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mapping__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug("using default value for %s: %s", key, str(value))
                setattr(self, key, value)
        return value

    @classmethod
    async def find_all(cls, where: str = None, args: list = None, **kwargs):
        """
        find objects by where clause.
        """
        sql = [cls.__select__]

        if where:
            sql.append("where")
            sql.append(where)

        args = args or []

        order_by = kwargs.get("orderBy", None)
        if order_by:
            sql.append("order by")
            sql.append(order_by)

        limit = kwargs.get("limit", None)
        if limit is not None:
            sql.append("limit")
            if isinstance(limit, int):
                sql.append("?")
            elif isinstance(limit, (tuple, list)) and len(limit) == 2:
                sql.append("?, ?")
                args.extend(limit)
            else:
                raise ValueError("Invalid limit value: %s", str(limit))
        ret = []
        for row in await select(" ".join(sql), args):
            kwargs = {}
            for i, field in enumerate(row.cursor_description):
                kwargs[field[0]] = row[i]
            ret.append(cls(**kwargs))
        return ret

    @classmethod
    async def find_number(cls, select_field, where: str = None, args: list = None):
        """find number by select and where"""
        sql = ["select {} _num_ from `{}`".format(select_field, cls.__table__)]
        if where:
            sql.append("where")
            sql.append(where)
        ret = await select(" ".join(sql), args, 1)
        return ret[0]["_num_"] if len(ret) else None

    @classmethod
    async def find(cls, primary_key):
        """find object by primary key"""
        ret = await select("{} where `{}`=?".format(cls.__select__, cls.__primary_key__), [primary_key], 1)
        return cls(**ret[0]) if len(ret) else None

    async def save_data(self):
        args = [self.get_value_or_default(field) for field in self.__fields__]
        args.append(self.get_value_or_default(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning("failed to insert record: affected rows: {} \n\tsql: {}\n\targs: {}",
                            rows, self.__insert__, args)

    async def update_data(self):
        args = [self.get_value_or_default(field) for field in self.__fields__]
        args.append(self.get_value_or_default(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warning("failed to update by primary key: affected rows: {} \n\tsql: {}\n\targs: {}",
                            rows, self.__update__, args)

    async def remove_data(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warning("failed to remove by primary key: affected rows: {} \n\tsql: {}\n\targs: {}",
                            rows, self.__delete__, args)
