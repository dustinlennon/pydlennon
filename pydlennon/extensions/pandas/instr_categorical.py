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

# ---------------------------------------------------------------------------------

# @Instrumented()
class ICategoricalDtype(pd.CategoricalDtype):
    name    = "icategory"

    @classmethod
    def construct_array_type(cls):
        return ICategorical

    @classmethod
    def _from_values_or_dtype(cls, values=None, categories=None, ordered = None, dtype = None):
        """
        Ref:./pandas/core/dtypes/dtypes.py:183
        """

        if dtype is not None:
            if isinstance(dtype, str):
                if dtype == cls.name:
                    dtype = cls(categories, ordered)
                else:
                    raise ValueError(f"Unknown dtype {repr(dtype)}")
            elif categories is not None or ordered is not None:
                raise ValueError(
                    "Cannot specify `categories` or `ordered` together with `dtype`."
                )
            elif not isinstance(dtype, cls):
                raise ValueError(f"Cannot not construct {cls.__name__} from {dtype}")
        elif cls.is_dtype(values):
            dtype = values.dtype._from_categorical_dtype(values.dtype, categories, ordered)
        else:
            dtype = cls(categories, ordered)

        return dtype


    def _repr(self):
        return pd.CategoricalDtype.__repr__(self)

    def __repr__(self):
        s = self._repr()
        return "I{0}".format(s)

    def update_dtype(self, dtype):
        # Ref:./pandas/core/dtypes/dtypes.py:518
        Klass = type(self)

        if isinstance(dtype, str) and dtype == "category":
            # dtype='category' should not change anything
            return self
        elif not self.is_dtype(dtype):
            raise ValueError(
                f"a {Klass.__name__} must be passed to perform an update, "
                f"got {repr(dtype)}"
            )
        else:
            # from here on, dtype is a CategoricalDtype
            dtype = xpd.cast(Klass, dtype)

        # update categories/ordered unless they've been explicitly passed as None
        new_categories = (
            dtype.categories if dtype.categories is not None else self.categories
        )
        new_ordered = dtype.ordered if dtype.ordered is not None else self.ordered

        return Klass(new_categories, new_ordered)


# ---------------------------------------------------------------------------------


# @Instrumented()
class ICategorical(pd.Categorical):
    _dtype  = ICategoricalDtype(ordered=False)
    _typ    = "icategorical"


    def __init__(self, values, categories=None, ordered=None, dtype=None, fastpath=False):
        # Ref:./pandas/core/arrays/categorical.py:300
        Dtype = type(self._dtype)

        dtype = Dtype._from_values_or_dtype(
            values, categories, ordered, dtype
        )

        if fastpath:
            self._codes = xpd.coerce_indexer_dtype(values, dtype.categories)
            self._dtype = self._dtype.update_dtype(dtype)
            return

        null_mask = np.array(False)

        if xpd.is_categorical_dtype(values):
            if dtype.categories is None:
                dtype = Dtype(values.categories, dtype.ordered)

        elif not isinstance(values, (xpd.ABCIndexClass, xpd.ABCSeries)):
            values = xpd.maybe_infer_to_datetimelike(values, convert_dates=True)
            if not isinstance(values, (np.ndarray, xpd.ExtensionArray)):
                values = xpd.com.convert_to_list_like(values)

                sanitize_dtype = np.dtype("O") if len(values) == 0 else None
                null_mask = xpd.isna(values)
                if null_mask.any():
                    values = [values[idx] for idx in np.where(~null_mask)[0]]
                values = xpd.sanitize_array(values, None, dtype=sanitize_dtype)

        if dtype.categories is None:
            try:
                codes, categories = xpd.factorize(values, sort=True)
            except TypeError as err:
                codes, categories = xpd.factorize(values, sort=False)
                if dtype.ordered:
                    raise TypeError(
                        "'values' is not ordered, please "
                        "explicitly specify the categories order "
                        "by passing in a categories argument."
                    ) from err
            except ValueError as err:
                raise NotImplementedError(
                    "> 1 ndim Categorical are not supported at this time"
                ) from err

            dtype = Dtype(categories, dtype.ordered)

        elif xpd.is_categorical_dtype(values.dtype):
            old_codes = xpd.extract_array(values).codes
            codes = xpd.recode_for_categories(
                old_codes, values.dtype.categories, dtype.categories
            )

        else:
            codes = xpd._get_codes_for_values(values, dtype.categories)

        if null_mask.any():
            full_codes = -np.ones(null_mask.shape, dtype=codes.dtype)
            full_codes[~null_mask] = codes
            codes = full_codes

        self._dtype = self._dtype.update_dtype(dtype)
        self._codes = xpd.coerce_indexer_dtype(codes, dtype.categories)


    @classmethod
    def _from_sequence(cls, scalars, *, dtype=None, copy=False):
        return cls(scalars, dtype=dtype)

    @property
    def _constructor(self):
        return type(self)

    @classmethod
    def _concat_same_type(cls, to_union):
        # Ref:./pandas/core/dtypes/concat.py:174

        sort_categories = False
        ignore_order = False

        if len(to_union) == 0:
            raise ValueError("No Categoricals to union")

        def _maybe_unwrap(x):
            if isinstance(x, (xpd.ABCCategoricalIndex, xpd.ABCSeries)):
                return x._values
            elif isinstance(x, cls):
                return x
            else:
                raise TypeError(f"all components to combine must be {cls.__name__}")

        to_union = [_maybe_unwrap(x) for x in to_union]
        first = to_union[0]

        if not all(
            is_dtype_equal(other.categories.dtype, first.categories.dtype)
            for other in to_union[1:]
        ):
            raise TypeError("dtype of categories must be the same")

        ordered = False
        if all(first._categories_match_up_to_permutation(other) for other in to_union[1:]):
            # identical categories - fastpath
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
            # different categories - union and recode
            cats = first.categories.append([c.categories for c in to_union[1:]])
            categories = cats.unique()
            if sort_categories:
                categories = categories.sort_values()

            new_codes = [
                xpd.recode_for_categories(c.codes, c.categories, categories) for c in to_union
            ]
            new_codes = np.concatenate(new_codes)
        else:
            # ordered - to show a proper error message
            if all(c.ordered for c in to_union):
                msg = f"to union ordered {cls.__name__}s, all categories must be the same"
                raise TypeError(msg)
            else:
                raise TypeError(f"{cls.__name__}.ordered must be the same")

        if ignore_order:
            ordered = False

        return cls(new_codes, categories=categories, ordered=ordered, fastpath=True)

    @classmethod
    def _from_sequence_of_strings(cls, strings, *, dtype=None, copy=False):
        scalars = xpd.to_numeric(strings, errors="raise")
        return cls._from_sequence(scalars, dtype=dtype, copy=copy)


# ---------------------------------------------------------------------------------

icd_gender = ICategoricalDtype((1,2))
icd_race   = ICategoricalDtype((1,2))

# ---------------------------------------------------------------------------------

if __name__ == "__main__":
    # See tests/extensions/test_ext_categorical.py for usage
    pass

