#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from www import config_default


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @classmethod
    def from_dict(cls, d: dict):
        attr_dict = cls()
        for k, v in d.items():
            attr_dict[k] = cls.from_dict(v) if isinstance(v, dict) else v
        return attr_dict


def merge(defaults, override):
    res = {}
    for k, v in defaults.items():
        if k in override:
            res[k] = merge(v, override[k]) if isinstance(v, dict) else override[k]
        else:
            res[k] = v
    return res


configs = config_default.configs
try:
    from www import config_override

    configs = merge(config_default.configs, config_override.configs)
except ImportError:
    config_override = None

configs = AttrDict.from_dict(configs)
