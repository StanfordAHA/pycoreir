from collections.abc import Mapping
import ctypes as ct
from .lib import libcoreir_c

def decode_cptr_and_free(ptr, free=True):
    #i = 0
    #pstr = ""
    #while ptr[i] != b'\0':
    #    pstr += ptr[i].decode()
    #    i += 1
    #libcoreir_c.COREFree(ptr)
    #return pstr

    MAX_STR_LEN = 1000000
    plen = 0
    while ptr[plen] != b'\0':
        plen +=1
        if plen > MAX_STR_LEN:
            raise ValueError("ptr does not have a null terminator")

    pstr = ptr[:plen].decode()
    if free:
        libcoreir_c.COREFree(ptr)
    return pstr


def raise_mapping(parent, core_return_type, return_type, iter_fn):
    c_keys = ct.POINTER(ct.POINTER(ct.c_char))()
    c_values = ct.POINTER(core_return_type)()
    size = ct.c_int()
    iter_fn(parent.ptr, ct.byref(c_keys), ct.byref(c_values), ct.byref(size))
    dct = {}
    for i in range(0, size.value):
        value = return_type(c_values[i], parent.context)
        dct[ct.cast(c_keys[i], ct.c_char_p).value.decode()] = value
        libcoreir_c.COREFree(c_keys[i])
    assert c_keys._b_needsfree_, "Expected pointer to be freed by ctypes"
    assert c_values._b_needsfree_, "Expected pointer to be freed by ctypes"
    return dct


class LazyDict(Mapping):
    """
    Lazy object that implements the ``dict[key]`` interface. Instead
    of building the dictionary explicitly for every call to config, we wait for
    the indexing function to be called and then use the api function
    """
    def __init__(self, parent, return_type, core_return_type, get_function, has_function, iter_function):
        self.parent = parent
        self.return_type = return_type
        self.core_return_type = core_return_type
        self.get_function = get_function
        self.has_function = has_function
        self.iter_function = iter_function

    def __contains__(self, key):
        return self.has_function(self.parent.ptr, str.encode(key))

    def __getitem__(self, key):
        if not key in self:
            raise KeyError("Could not find key: {}".format(key))
        return self.return_type(
                   self.get_function(self.parent.ptr,
                                     str.encode(key)),
                   self.parent.context)

    def __iter__(self):
        dct = raise_mapping(
            self.parent,
            self.core_return_type,
            self.return_type,
            self.iter_function)
        return iter(dct)

    def __len__(self):
        # TODO: Should just be an API call
        _len = 0
        for _ in self:
            _len += 1
        return _len


    def __setitem__(self, key, value):
        raise NotImplementedError()
