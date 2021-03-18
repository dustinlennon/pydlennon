import numpy as np
import logging

import re

import extensions.pandas as xpd
from patterns.proxy import Proxy


_attr_rex = re.compile(r"^_{0,1}[A-Za-z0-9][A-Za-z0-9_]*")

# ---------------------------------------------------------------------------------

categoricaldtype_attrs_blacklist = ['construct_array_type', '_from_values_or_dtype', 'name']
categoricaldtype_attrs =    [ a for a in dir(xpd.CategoricalDtype) if _attr_rex.match(a) and a not in categoricaldtype_attrs_blacklist] \
                          + ['__repr__', '__hash__', '__getstate__']


@Proxy("_cat_dtype", xpd.CategoricalDtype, categoricaldtype_attrs)
class ExtCategoricalDtype(xpd.PandasExtensionDtype):
    """
    Behaves very similarly to the usual CategoricalDtype but with added functionality; namely, 
    multiple codings are maintained within the object.
    """
    name = "wrapped_category"

    def __init__(self, levels = None, *args, **kw):
        self._ext = list(zip(*levels))
        self._cat_dtype = xpd.CategoricalDtype(self._ext[0], *args, **kw)

    def __call__(self, srcidx):
        self._logger.info("ExtCategoricalDtype.__call__")
        obj = object.__new__( type(self) )
        obj._ext = self._ext
        obj._cat_dtype = xpd.CategoricalDtype(self._ext[srcidx], ordered = self._cat_dtype.ordered)
        return obj

    @classmethod 
    def build_from_existing(cls, ext, srcidx, *args, **Kw):
        cls._logger.info("ExtCategoricalDtype.build_from_existing")
        obj = object.__new__(cls)
        obj._ext = ext
        obj._cat_dtype = xpd.CategoricalDtype(obj._ext[srcidx], *args, **Kw)
        return obj

    @classmethod
    def build_default(cls):
        cls._logger.info("ExtCategoricalDtype.build_default")
        obj = object.__new__(cls)
        obj._cat_dtype = xpd.CategoricalDtype(ordered=False)
        return obj

    @classmethod
    def construct_array_type(cls):
        cls._logger.info("ExtCategoricalDtype.construct_array_type")
        return ExtCategorical


# ---------------------------------------------------------------------------------

categorical_attrs_blacklist = ['_from_sequence_of_strings', '_concat_same_type', '_from_sequence', 'dtype', '_dtype']
categorical_attrs =     [ a for a in dir(xpd.Categorical) if _attr_rex.match(a) and a not in categorical_attrs_blacklist] \
                      + ['__repr__', '__len__', "__getitem__"]

@Proxy("_cat", xpd.Categorical, categorical_attrs)
class ExtCategorical(xpd.ExtensionArray):       

    _dtype = ExtCategoricalDtype.build_default()

    def __init__(self, *args, **kw):
        dtype = kw.pop('dtype', None)
        if isinstance( dtype, ExtCategoricalDtype ):
            kw['dtype'] = dtype._cat_dtype
            self._dtype = dtype

        self._cat = xpd.Categorical(*args, **kw)

    @property
    def dtype(self):
        return self._dtype

    @classmethod
    def _from_sequence(cls, scalars, *, dtype=None, copy=False):
        # pandas.core.arrays.categorical.py:387
        cls._logger.info("ExtCategorical._from_sequence")
        return ExtCategorical(scalars, dtype=dtype)

    @classmethod
    def _from_sequence_of_strings(cls, strings, *, dtype, copy=False):
        # pandas.io.parsers.py:1797; pandas.core.arrays.categorical.py:463
        cls._logger.info("ExtCategorical._from_sequence_of_strings")

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

        return cls(codes, dtype=dtype, fastpath=True)

    @classmethod
    def _concat_same_type(cls, to_union, axis=0):
        # pandas.core.dtypes.concat.py:175
        cls._logger.info("ExtCategorical._concat_same_type")

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

        instance = cls(new_codes, categories=categories, ordered=ordered, fastpath=True)
        instance._dtype = first._dtype
        return instance


# ---------------------------------------------------------------------------------

xcat_attrs_blacklist = ['map']
xcat_attr =     [ a for a in dir(xpd.Series) if _attr_rex.match(a) and a not in xcat_attrs_blacklist] \
              + ['__repr__', '__len__', "__getitem__"]


@xpd.register_series_accessor('xcat')
@Proxy("_series", xpd.Series, xcat_attr)
class ExtCategoricalAccessor:

    def __init__(self, obj):
        if not isinstance(obj.dtype, ExtCategoricalDtype):
            raise AttributeError("Can only use .xcat accessor with ExtCategorical values")

        self._xcdtype   = obj.dtype
        self._series    = xpd.Series(obj.values._cat)


    def relevel(self, dstidx):
        new_dtype = self._xcdtype(dstidx)

        srccat = self._xcdtype.categories
        dstcat = new_dtype.categories

        m = dict(zip(srccat, dstcat))

        s = xpd.Series( self._series.values.map(m), dtype = new_dtype)
        return s


# ---------------------------------------------------------------------------------


if __name__ == "__main__":
    # See tests/extensions/test_ext_categorical.py for usage
    pass

