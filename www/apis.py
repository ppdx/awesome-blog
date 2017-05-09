#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math


class Page:
    def __init__(self, item_count, page_index=1, page_size=10):
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = int(math.ceil(item_count / page_size))
        if item_count == 0 or page_index > self.page_count:
            self.page_index = 1
            self.offset = 0
            self.limit = 0
        else:
            self.page_index = page_index
            self.offset = page_size * (page_index - 1)
            self.limit = self.page_size

    @property
    def has_next(self):
        return self.page_index < self.page_count

    @property
    def has_previous(self):
        return self.page_index > 1

    def __str__(self):
        return "item count: {}, page count: {}, page index: {}, page size: {}, offset: {}, limit: {}".format(
                self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit
        )

    __repr__ = __str__


class APIError(Exception):
    """the base APIError which contains error(required), data(optional), message(optional)."""

    def __init__(self, error, data="", message=""):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class APIValueError(APIError):
    """Indicate the input value has error or invalid. The data specifies the error field of input form."""

    def __init__(self, field, message=""):
        super(APIValueError, self).__init__("value:invalid", field, message)


class APIResourceNotFoundError(APIError):
    """Indicate the resource was not found. The data specifies the resource name."""

    def __init__(self, field, message=""):
        super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)


class APIPermissionError(APIError):
    """Indicate the api has no permission."""

    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)
