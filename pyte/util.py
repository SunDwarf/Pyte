"""
Miscellaneous utilities.
"""
import collections
import dis

import sys

from pyte.exc import ValidationError
from . import tokens
import pyte

# Python 3.6 specific things.
# Bytecode format changed in Py 3.6 slightly.
# It's mostly the same, just shorter.
# The most notable things:
# All instructions are now 16-bit.
# This makes life easier.
# It also means all 'raw' ints have to be wrapped in an `ensure_instruction` function.

PY36 = sys.version_info[0:2] >= (3, 6)


def ensure_instruction(instruction: int):
    """
    Wraps an instruction to be Python 3.6+ compatible.

    This does nothing on Python 3.5 and below.

    This is most useful for operating on bare, single-width instructions such as ``RETURN_FUNCTION`` in a version
    portable way.

    :param instruction: The instruction integer to use.
    :return: A safe bytes object, if applicable.
    """
    if PY36:
        return instruction.to_bytes(2, byteorder="little")
    else:
        return instruction.to_bytes(1, byteorder="little")


def pack_value(index: int) -> bytes:
    """
    Small helper value to pack an index value into bytecode.

    This is used for version compat between 3.5- and 3.6+

    :param index: The item to pack.
    :return: The packed item.
    """
    if PY36:
        return index.to_bytes(1, byteorder="little")
    else:
        return index.to_bytes(2, byteorder="little")


def generate_simple_call(opcode, index):
    bs = b""
    # add the opcode
    bs += opcode.to_bytes(1, byteorder="little")
    # Add the index
    if isinstance(index, int):
        if PY36:
            bs += index.to_bytes(1, byteorder="little")
        else:
            bs += index.to_bytes(2, byteorder="little")
    else:
        bs += index
    # return it
    return bs


def generate_bytecode_from_obb(obb: object, previous: bytes) -> bytes:
    # Generates bytecode from a specified object, be it a validator or an int or bytes even.
    if isinstance(obb, pyte.superclasses._PyteOp):
        return obb.to_bytes(previous)
    elif isinstance(obb, (pyte.superclasses._PyteAugmentedComparator,
                          pyte.superclasses._PyteAugmentedValidator._FakeMathematicalOP)):
        return obb.to_bytes(previous)
    elif isinstance(obb, pyte.superclasses._PyteAugmentedValidator):
        obb.validate()
        return obb.to_load()
    elif isinstance(obb, int):
        return obb.to_bytes((obb.bit_length() + 7) // 8, byteorder="little") or b''
    elif isinstance(obb, bytes):
        return obb
    else:
        raise TypeError("`{}` was not a valid bytecode-encodable item".format(obb))


def generate_load_global(index) -> bytes:
    return generate_simple_call(tokens.LOAD_GLOBAL, index)


def generate_load_fast(index) -> bytes:
    """
    Generates a LOAD_FAST operation.
    """
    return generate_simple_call(tokens.LOAD_FAST, index)


def generate_load_const(index) -> bytes:
    return generate_simple_call(tokens.LOAD_CONST, index)


# https://stackoverflow.com/a/2158532
def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, (str, bytes)):
            for sub in flatten(el):
                yield sub
        else:
            yield el


# "fixed" functions

def _get_const_info(const_index, const_list):
    """Helper to get optional details about const references

       Returns the dereferenced constant and its repr if the constant
       list is defined.
       Otherwise returns the constant index and its repr().
    """
    argval = const_index
    if const_list is not None:
        try:
            argval = const_list[const_index]
        except IndexError:
            raise ValidationError("Consts value out of range: {}".format(const_index))
    return argval, repr(argval)


def _get_name_info(name_index, name_list):
    """Helper to get optional details about named references

       Returns the dereferenced name as both value and repr if the name
       list is defined.
       Otherwise returns the name index and its repr().
    """
    argval = name_index
    if name_list is not None:
        try:
            argval = name_list[name_index]
        except IndexError:
            raise ValidationError("Names value out of range: {}".format(name_index))
        argrepr = argval
    else:
        argrepr = repr(argval)
    return argval, argrepr


dis._get_const_info = _get_const_info
dis._get_name_info = _get_name_info

if sys.version_info[0:2] < (3, 4):
    from pyte import backports

    backports.apply()
