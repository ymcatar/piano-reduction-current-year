from collections.abc import Sequence
import importlib

from music21 import chord


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


def iter_notes(stream, recurse=False):
    '''
    Given a stream, return an iterator that yields all notes, including those
    inside a chord.
    '''
    if recurse:
        stream = stream.recurse(skipSelf=False)
    for n in stream.notes:
        if isinstance(n, chord.Chord):
            for n2 in n:
                yield n2
        else:
            yield n


def iter_notes_with_offset(stream, recurse=False):
    '''
    Given a stream, return an iterator that yields all notes with the offset
    value, including those inside a chord.

    Note that Notes inside a chord always have an offset value of 0.
    '''
    if recurse:
        stream = stream.recurse(skipSelf=False)
    for n in stream.notes:
        if isinstance(n, chord.Chord):
            for n2 in n:
                yield n2, n.offset
        else:
            yield n, n.offset
