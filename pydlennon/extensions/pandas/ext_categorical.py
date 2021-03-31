import numpy as np
import logging

import re

import pydlennon.extensions.pandas as xpd
from pydlennon.patterns.proxy import Proxy
from pydlennon.instrumented import Instrumented


# ---------------------------------------------------------------------------------

#     def __call__(self, srcidx):
#         self._logger.info("ExtCategoricalDtype.__call__")
#         obj = object.__new__( type(self) )
#         obj._ext = self._ext
#         obj._cat_dtype = xpd.CategoricalDtype(self._ext[srcidx], ordered = self._cat_dtype.ordered)
#         return obj

#     @classmethod 
#     def build_from_existing(cls, ext, srcidx, *args, **Kw):
#         cls._logger.info("ExtCategoricalDtype.build_from_existing")
#         obj = object.__new__(cls)
#         obj._ext = ext
#         obj._cat_dtype = xpd.CategoricalDtype(obj._ext[srcidx], *args, **Kw)
#         return obj

#     @classmethod
#     def build_default(cls):
#         cls._logger.info("ExtCategoricalDtype.build_default")
#         obj = object.__new__(cls)
#         obj._cat_dtype = xpd.CategoricalDtype(ordered=False)
#         return obj

#     @classmethod
#     def construct_array_type(cls):
#         cls._logger.info("ExtCategoricalDtype.construct_array_type")
#         return ExtCategorical




@Instrumented(logging_level=logging.INFO)
class ExtCategoricalDtype(xpd.CategoricalDtype):
    name = "ext_category"

    def _finalize(self, categories, ordered, fastpath = False):
        """
        pandas.core.dtypes.dtypes.py:308
        """
        if ordered is not None:
            self.validate_ordered(ordered)

        if categories is not None:
            try:
                self._ext = list(zip(*categories))
            except TypeError:
                pass
            else:
                categories = self._ext[0]

            categories = self.validate_categories(categories, fastpath=fastpath)

        self._categories = categories
        self._ordered = ordered


    @classmethod
    def construct_array_type(cls):
        return ExtCategorical


    def __call__(self, srcidx):
        categories = list(zip(*self._ext))
        obj = ExtCategoricalDtype(categories, self.ordered)
        obj._categories = xpd.CategoricalDtype(self._ext[srcidx], ordered = obj.ordered).categories
        return obj


    @classmethod
    def construct_from_string(cls, string):
        """
        pandas.core.dtypes.dtypes.py:278
        """
        if not isinstance(string, str):
            raise TypeError(
                f"'construct_from_string' expects a string, got {type(string)}"
            )
        if string != cls.name:
            raise TypeError(f"Cannot construct an 'ExtCategoricalDtype' from '{string}'")

        return cls(ordered=None)


    def update_dtype(self, dtype):
        """
        pandas.core.dtypes.dtypes.py:518
        """
        if isinstance(dtype, str) and dtype == "ext_category":
            # dtype='category' should not change anything
            return self
        elif not self.is_dtype(dtype):
            raise ValueError(
                f"a CategoricalDtype must be passed to perform an update, "
                f"got {repr(dtype)}"
            )
        else:
            # from here on, dtype is an ExtCategoricalDtype
            dtype = xpd.cast(ExtCategoricalDtype, dtype)

        # update categories/ordered unless they've been explicitly passed as None

        # new_categories = (
        #     dtype.categories if dtype.categories is not None else self.categories
        # )

        if dtype._ext is not None:
            new_categories  = list(zip(*dtype._ext))
            prev_categories = tuple( dtype.categories.to_list() )
            ridx            = dtype._ext.index( prev_categories )

            # if ridx != 0:
            #     import pdb
            #     pdb.set_trace()


        elif dtype.categories is not None:
            new_categories = dtype.categories

        else:
            new_categories = self.categories

        new_ordered = dtype.ordered if dtype.ordered is not None else self.ordered

        obj             = ExtCategoricalDtype(new_categories, new_ordered)
        obj._categories = obj.validate_categories(obj._ext[ridx], fastpath=True)

        return obj


# ---------------------------------------------------------------------------------


@Instrumented(logging_level=logging.INFO)
class ExtCategorical(xpd.Categorical):

    _dtype = ExtCategoricalDtype(ordered=False)
    _typ = "ext_categorical"


    @classmethod
    def _concat_same_type(cls, to_union, axis=0):
        # pandas.core.dtypes.concat.py:175
        sort_categories = False
        ignore_order = False

        if len(to_union) == 0:
            raise ValueError("No Categoricals to union")

        def _maybe_unwrap(x):
            if isinstance(x, (xpd.ABCCategoricalIndex, xpd.ABCSeries)):
                return x._values
            elif isinstance(x, xpd.Categorical) or isinstance(x, ExtCategorical):
                return x
            else:
                raise TypeError("all components to combine must be Categorical")

        to_union = [_maybe_unwrap(x) for x in to_union]
        first = to_union[0]

        if not all(
            xpd.is_dtype_equal(other.categories.dtype, first.categories.dtype)
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
                xpd.recode_for_categories(c.codes, c.categories, categories) for c in to_union
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

        # need to modify the _dtype before returning
        # instance = cls(new_codes, categories=categories, ordered=ordered, fastpath=True)
        instance = cls(new_codes, dtype = first._dtype, fastpath=True)
        return instance


    @property
    def _constructor(self):
        return ExtCategorical


    @classmethod
    def _from_sequence(cls, scalars, *, dtype=None, copy=False):
        # pandas.core.arrays.categorical.py:387
        return ExtCategorical(scalars, dtype=dtype)


    @classmethod
    def _from_sequence_of_strings(cls, strings, *, dtype, copy=False):
        # pandas.io.parsers.py:1797; pandas.core.arrays.categorical.py:463
        cats = xpd.Index(strings).unique().dropna()
        inferred_categories = cats
        inferred_codes = cats.get_indexer(strings)
        true_values = None

        # known_categories == True
        if dtype.categories.is_numeric():
            cats = xpd.to_numeric(inferred_categories, errors="coerce")
        elif xpd.is_datetime64_dtype(dtype.categories):
            cats = xpd.to_datetime(inferred_categories, errors="coerce")
        elif xpd.is_timedelta64_dtype(dtype.categories):
            cats = xpd.to_timedelta(inferred_categories, errors="coerce")
        elif dtype.categories.is_boolean():
            if true_values is None:
                true_values = ["True", "TRUE", "true"]

            cats = cats.isin(true_values)

        categories = dtype.categories
        codes = xpd.recode_for_categories(inferred_codes, cats, categories)

        obj = cls(codes, dtype=dtype, fastpath=True)
        return obj



# ---------------------------------------------------------------------------------



#     def take(self, indices, *, allow_fill = False, fill_value = None, axis = 0):
#         self._logger.info("ExtCategorical.take")
#         if allow_fill:
#             fill_value = self._validate_fill_value(fill_value)

#         from pandas.core.algorithms import take
#         new_data = take(
#             self._ndarray,
#             indices,
#             allow_fill=allow_fill,
#             fill_value=fill_value,
#             axis=axis,
#         )

#         import pdb
#         pdb.set_trace()

#         df = self._from_backing_data(new_data)
#         return df



# ---------------------------------------------------------------------------------

@xpd.register_series_accessor('xcat')
class ExtCategoricalAccessor:

    def __init__(self, obj):
        if not isinstance(obj.dtype, ExtCategoricalDtype):
            raise AttributeError("Can only use .xcat accessor with ExtCategorical values")

        self._xcdtype   = obj.dtype
        self._obj       = obj


    def relevel(self, dstidx):
        new_dtype = self._xcdtype(dstidx)

        srccat = self._xcdtype.categories
        dstcat = new_dtype.categories

        print(srccat)
        print(dstcat)

        m = dict(zip(srccat, dstcat))

        s = xpd.Series( self._obj.values.map(m), dtype = new_dtype)
        return s



# xcat_attrs_blacklist = ['map']
# xcat_attr =     [ a for a in dir(xpd.Series) if _attr_rex.match(a) and a not in xcat_attrs_blacklist] \
#               + ['__repr__', '__len__', "__getitem__"]


# @xpd.register_series_accessor('xcat')
# @Proxy("_series", xpd.Series, xcat_attr)
# class ExtCategoricalAccessor:

#     def __init__(self, obj):
#         if not isinstance(obj.dtype, ExtCategoricalDtype):
#             raise AttributeError("Can only use .xcat accessor with ExtCategorical values")

#         self._xcdtype   = obj.dtype
#         self._series    = xpd.Series(obj.values._cat)


#     def relevel(self, dstidx):
#         new_dtype = self._xcdtype(dstidx)

#         srccat = self._xcdtype.categories
#         dstcat = new_dtype.categories

#         m = dict(zip(srccat, dstcat))

#         s = xpd.Series( self._series.values.map(m), dtype = new_dtype)
#         return s


# ---------------------------------------------------------------------------------


if __name__ == "__main__":
    # See tests/extensions/test_ext_categorical.py for usage

    import IPython
    ipy = IPython.get_ipython()
    if ipy:
        if  not 'autoreload' in ipy.magics_manager.shell.extension_manager.loaded:
            ipy.run_line_magic("load_ext", "autoreload")
            ipy.run_line_magic("autoreload","2")


    import numpy as np
    import pandas as pd
    import logging

    from pydlennon.extensions.pandas.ext_categorical import ExtCategoricalDtype, ExtCategorical
    from pydlennon.tests.extensions.test_ext_categorical import ProxyTestCase

    logging.basicConfig(level=logging.INFO)

    self = ProxyTestCase()
    self.setUp()

    # xc  = ExtCategorical._from_sequence_of_strings(self.gender_data_s, dtype=self.xcdtype_gender)
    # s   = pd.Series(xc)

    kw = {
        'dtype' : {
            'gender' : self.xcdtype_gender,
            'race'   : self.xcdtype_race
        },
        'usecols' : ['record_id', 'gender', 'race']
    }
    df  = self.loader(**kw)
    df.loc[19644, 'race'] = np.nan


    s = df.gender
    m = {1: 'male', 2: 'female'}
    s2 = s.map(m)
    d2 = s.dtype(1)

    ExtCategorical(s2, dtype=d2)


    # df.gender.xcat.relevel(1)

    # z  = df.dropna()
    # z.gender.xcat.relevel(1)


