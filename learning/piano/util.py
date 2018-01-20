from collections.abc import Sequence
import importlib


def import_symbol(path):
    module, symbol = path.rsplit('.', 1)
    return getattr(importlib.import_module(module), symbol)


def load_algorithm(path, args, kwargs):
    return import_symbol(path)(*args, **kwargs)


def ensure_algorithm(obj):
    if isinstance(obj, Sequence):
        return load_algorithm(*obj)
    else:
        return obj


def dump_algorithm(algo):
    return (type(algo).__module__ + '.' + type(algo).__qualname__, *algo.args)
