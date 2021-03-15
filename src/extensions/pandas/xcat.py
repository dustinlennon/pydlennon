try:
    ipy
except NameError:
    import IPython
    ipy = IPython.get_ipython()
    if ipy:
        ipy.run_line_magic("load_ext", "autoreload")
        ipy.run_line_magic("autoreload","2")


import numpy as np

from pandas.core.dtypes.dtypes import PandasExtensionDtype
from pandas.core.arrays.base import ExtensionArray

from pandas import Categorical, CategoricalDtype

from pandas import Index, to_datetime, to_numeric, to_timedelta

from pandas.core.dtypes.common import (
    is_datetime64_dtype,
    is_timedelta64_dtype,
    is_categorical_dtype
)

from pandas.core.dtypes.generic import ABCCategoricalIndex, ABCRangeIndex, ABCSeries

from pandas.core.dtypes.cast import (
    coerce_indexer_dtype,
)

from pandas.core.arrays.categorical import recode_for_categories

from pandas.api.extensions import register_series_accessor

from util.delegate import Delegate

import re
import pdb

attr_rex = re.compile(r"^_{0,1}[A-Za-z0-9][A-Za-z0-9_]*")

# ---------------------------------------------------------------------------------

categoricaldtype_attrs_blacklist = ['T', 'construct_array_type', 'name']
categoricaldtype_attrs =    [ a for a in dir(CategoricalDtype) if attr_rex.match(a) and a not in categoricaldtype_attrs_blacklist] \
                          + ['__repr__', '__hash__', '__getstate__']


@Delegate("_delegate", CategoricalDtype, categoricaldtype_attrs)
class ExtCategoricalDtype(PandasExtensionDtype):
    name = "wrapped_category"

    def __init__(self, levels = None, ext = None, srcidx = 0):
        if levels is not None and ext is None:
            self._ext = list(zip(*levels))
            self._delegate = CategoricalDtype(self._ext[srcidx])
        elif levels is None and ext is not None:
            self._ext = ext
            self._delegate = CategoricalDtype(self._ext[srcidx])
        else:
            self._delegate = CategoricalDtype(ordered=False)

    @classmethod
    def construct_array_type(cls):
        # print("[D]ExtCategoricalDtype<class>.construct_array_type")
        return ExtCategorical



# ---------------------------------------------------------------------------------

categorical_attrs_blacklist = ['_from_sequence_of_strings', '_concat_same_type', 'dtype', '_dtype']
categorical_attrs =     [ a for a in dir(Categorical) if attr_rex.match(a) and a not in categorical_attrs_blacklist] \
                      + ['__repr__', '__len__', "__getitem__"]

@Delegate("_delegate", Categorical, categorical_attrs)
class ExtCategorical(ExtensionArray):       

    _dtype = ExtCategoricalDtype()

    def __init__(self, *args, **kw):
        dtype = kw.pop('dtype', None)
        if isinstance( dtype, ExtCategoricalDtype ):
            kw['dtype'] = dtype._delegate
            self._dtype = dtype

        self._delegate = Categorical(*args, **kw)

    @property
    def dtype(self):
        return self._dtype

    @classmethod
    def _from_sequence_of_strings(cls, strings, *, dtype, copy=False):
        # pandas.io.parsers.py:1797; pandas.core.arrays.categorical.py:463
        # print("[D]ExtCategorical<class>._from_sequence_of_strings")
        cats = Index(strings).unique().dropna()
        inferred_categories = cats
        inferred_codes = cats.get_indexer(strings)
        true_values = None

        # known_categories == True
        if dtype.categories.is_numeric():
            cats = to_numeric(inferred_categories, errors="coerce")
        elif is_datetime64_dtype(dtype.categories):
            cats = to_datetime(inferred_categories, errors="coerce")
        elif is_timedelta64_dtype(dtype.categories):
            cats = to_timedelta(inferred_categories, errors="coerce")
        elif dtype.categories.is_boolean():
            if true_values is None:
                true_values = ["True", "TRUE", "true"]

            cats = cats.isin(true_values)

        categories = dtype.categories
        codes = recode_for_categories(inferred_codes, cats, categories)

        return cls(codes, dtype=dtype, fastpath=True)

    @classmethod
    def _concat_same_type(cls, to_union, axis=0):
        # pandas.core.dtypes.concat.py:175
        # print("[D]ExtCategorical<class>._concat_same_type")

        sort_categories = False
        ignore_order = False

        if len(to_union) == 0:
            raise ValueError("No Categoricals to union")

        def _maybe_unwrap(x):
            if isinstance(x, (ABCCategoricalIndex, ABCSeries)):
                return x._values
            elif isinstance(x, Categorical) or isinstance(x, ExtCategorical):
                return x
            else:
                raise TypeError("all components to combine must be Categorical")

        to_union = [_maybe_unwrap(x) for x in to_union]
        first = to_union[0]

        if not all(
            is_dtype_equal(other.categories.dtype, first.categories.dtype)
            for other in to_union[1:]
        ):
            raise TypeError("dtype of categories must be the same")

        ordered = False
        if all(first._categories_match_up_to_permutation(other) for other in to_union[1:]):
            categories = first.categories
            ordered = first.ordered

            all_codes = [first._encode_with_my_categories(x)._codes for x in to_union]
            new_codes = np.concatenate(all_codes)

            if sort_categories and not ignore_order and ordered:
                raise TypeError("Cannot use sort_categories=True with ordered Categoricals")

            if sort_categories and not categories.is_monotonic_increasing:
                categories = categories.sort_values()
                indexer = categories.get_indexer(first.categories)

                from pandas.core.algorithms import take_1d

                new_codes = take_1d(indexer, new_codes, fill_value=-1)
        elif ignore_order or all(not c.ordered for c in to_union):
            cats = first.categories.append([c.categories for c in to_union[1:]])
            categories = cats.unique()
            if sort_categories:
                categories = categories.sort_values()

            new_codes = [
                recode_for_categories(c.codes, c.categories, categories) for c in to_union
            ]
            new_codes = np.concatenate(new_codes)
        else:
            if all(c.ordered for c in to_union):
                msg = "to union ordered Categoricals, all categories must be the same"
                raise TypeError(msg)
            else:
                raise TypeError("Categorical.ordered must be the same")

        if ignore_order:
            ordered = False

        instance = cls(new_codes, categories=categories, ordered=ordered, fastpath=True)
        instance._dtype = first._dtype
        return instance

# ---------------------------------------------------------------------------------

@register_series_accessor('xcat')
class ExtCategoricalAccessor:
    def __init__(self, pobj):
        if not isinstance(pobj.dtype, ExtCategoricalDtype):
            raise AttributeError("Can only use .ext accessor with ExtCategorical values")
        self._obj   = pobj

    @property
    def delegate(self):
        return self._obj.values._delegate

    @property
    def dtype(self):
        return self._obj.dtype

    def map(self, dstidx):
        ext     = self.dtype._ext
        values  = self.delegate
        cats    = tuple(values.categories.tolist())

        srcidx = None
        for i in range(len(ext)):
            if cats == ext[i]:
                srcidx = i

        if srcidx == None:
            raise RuntimeError("categories don't match any known definition")

        dmap        = dict(zip(ext[srcidx], ext[dstidx]))
        delegate    = values.map( dmap )

        instance = ExtCategorical(delegate.to_list(), categories = delegate.categories, ordered=delegate.ordered)
        instance._dtype = ExtCategoricalDtype( ext = ext, srcidx = srcidx )
        return instance


# ---------------------------------------------------------------------------------


if __name__ == "__main__":

    import pandas as pd

    import sys
    import os
    path = r"/home/dnlennon/Workspace/Analyses/2021.ARM/venv/lib/python3.8/site-packages/pandas"
    pdb_cmd = """ \
        python3 -m pdb -c \
        "b {path}/io/parsers.py:1796" \
        -c c ./extensions/categorical.py
    """.format(path=path).strip()
    # print(pdb_cmd)

    # sys.exit(0)



    xc_type     = ExtCategoricalDtype( [
                                            (1, 'male', 0),
                                            (2, 'female', 1)
                                        ])
    
    c_type      = CategoricalDtype([1,2])

    strings     = ["1","1","2","2","1","2"]
    xc          = ExtCategorical._from_sequence_of_strings(strings, dtype=xc_type)

    cats        = Index(strings).unique().dropna()
    c           = Categorical._from_inferred_categories(cats, cats.get_indexer(strings), c_type)

    pd.Series(xc)


    config = {
        'path' : "foo.csv",
        'kwargs' : {
            'dtype' : {
                'gender'    : xc_type,
                'ideo'      : 'category',
                'partyid3'  : 'category',
                'race'      : 'category',
            },
            'index_col' : 0,
            'header' : 0,
            'names' : [
                'record_id',
                'gender',
                'ideo',
                'partyid3',
                'race'
            ],
            'nrows' : 10,
        }
    }


    df = pd.read_csv(config['path'], **config['kwargs'])


    dtype = df.gender.xcat.dtype
    cat   = df.gender.xcat.delegate

    s = pd.Series( df.gender.xcat.map(1) )
    print(s)