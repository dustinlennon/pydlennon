
# try:
#     import IPython
#     ipy = IPython.get_ipython()
#     if ipy:
#         if  not 'autoreload' in ipy.magics_manager.shell.extension_manager.loaded:
#             ipy.run_line_magic("load_ext", "autoreload")
#             ipy.run_line_magic("autoreload","2")
# except ModuleNotFoundError:
#     pass


import numpy as np
import logging

import re
import io

import pandas as pd
from pydlennon.patterns.instrumented import Instrumented
import pydlennon.extensions.pandas as xpd

from pydlennon.extensions.pandas.instr_categorical import ICategoricalDtype, ICategorical


# ---------------------------------------------------------------------------------

@Instrumented()
class ExtCategoricalDtype(ICategoricalDtype):
    name    = "ext_category"


    @classmethod
    def construct_array_type(cls):
        return ExtCategorical


    def __repr__(self):
        s = self._repr()
        return "Ext{0}".format(s)


    def __call__(self, srcidx):
        """
        change the category to another group
        """
        categories = list(zip(*self._ext))
        obj = ExtCategoricalDtype(categories, self.ordered)
        obj._categories = xpd.CategoricalDtype(self._ext[srcidx], ordered = obj.ordered).categories
        return obj


    def _finalize(self, categories, ordered, fastpath = False):
        """
        pandas.core.dtypes.dtypes.py:308
        """
        if ordered is not None:
            self.validate_ordered(ordered)

        if categories is not None:
            try:
                lol = [ isinstance(i,(list,tuple)) for i in categories ]
                if not all( lol ):
                    raise TypeError("categories was not specified as a list of lists")
            except TypeError:
                self._ext = [ tuple(categories) ]
            else:
                # N.B. this sets the categories to the first group
                self._ext = list(zip(*categories))
                categories = self._ext[0]   

            self._logger.info(f"\t ---->  {self._ext}")
            categories = self.validate_categories(categories, fastpath=fastpath)

        self._categories = categories
        self._ordered = ordered


    def update_dtype(self, dtype):
        """
        pandas.core.dtypes.dtypes.py:518
        """
        Klass = type(self)

        if isinstance(dtype, str) and dtype == self.name:
            return self
        elif not self.is_dtype(dtype):
            raise ValueError(
                f"a {Klass.__name__} must be passed to perform an update, "
                f"got {repr(dtype)}"
            )
        else:
            dtype = xpd.cast(Klass, dtype)

        # update categories/ordered unless they've been explicitly passed as None

        new_ordered = dtype.ordered if dtype.ordered is not None else self.ordered

        ridx = 0
        if len(dtype._ext) >= 2:
            new_categories  = list(zip(*dtype._ext))
            prev_categories = tuple( dtype.categories.to_list() )
            ridx            = dtype._ext.index( prev_categories )

        elif dtype.categories is not None:
            new_categories = dtype.categories

        else:
            new_categories = self.categories

        # create a new dtype object
        obj = Klass(new_categories, new_ordered)
        if ridx > 0:
            obj._categories = obj.validate_categories(obj._ext[ridx], fastpath=True)

        return obj


# ---------------------------------------------------------------------------------

@Instrumented()
class ExtCategorical(ICategorical):
    _dtype  = ExtCategoricalDtype(ordered=False)
    _typ    = "ext_categorical"


    @classmethod
    def _concat_same_type(cls, to_union):
        first       = to_union[0]

        obj             = super()._concat_same_type(to_union)
        obj.dtype._ext  = first.dtype._ext

        return obj

# ---------------------------------------------------------------------------------

@xpd.register_series_accessor('xcat')
class ExtCategoricalAccessor:

    def __init__(self, pobj):
        if not isinstance(pobj.dtype, ExtCategoricalDtype):
            raise AttributeError("Can only use .xcat accessor with ExtCategorical values")

        self._xcdtype   = pobj.dtype
        self._obj       = pobj


    def relevel(self, dstidx):
        new_dtype = self._xcdtype(dstidx)

        srccat = self._xcdtype.categories
        dstcat = new_dtype.categories

        m = dict(zip(srccat, dstcat))

        s = pd.Series( self._obj.values.map(m), dtype = new_dtype, index=self._obj.index)
        return s

# ---------------------------------------------------------------------------------


if __name__ == "__main__":
    # See tests/extensions/test_ext_categorical.py for usage
    pass