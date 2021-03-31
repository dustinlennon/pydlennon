from csv import QUOTE_NONNUMERIC
from functools import partial
import operator
from shutil import get_terminal_size
from typing import Dict, Hashable, List, Sequence, Type, TypeVar, Union, cast
from warnings import warn

import numpy as np

from pandas._config import get_option

from pandas._libs import NaT, algos as libalgos, hashtable as htable
from pandas._libs.lib import no_default
from pandas._typing import ArrayLike, Dtype, Ordered, Scalar
from pandas.compat.numpy import function as nv
from pandas.util._decorators import cache_readonly, deprecate_kwarg
from pandas.util._validators import validate_bool_kwarg, validate_fillna_kwargs

from pandas.core.dtypes.cast import (
    coerce_indexer_dtype,
    maybe_cast_to_extension_array,
    maybe_infer_to_datetimelike,
)
from pandas.core.dtypes.common import (
    ensure_int64,
    ensure_object,
    is_categorical_dtype,
    is_datetime64_dtype,
    is_dict_like,
    is_dtype_equal,
    is_extension_array_dtype,
    is_hashable,
    is_integer_dtype,
    is_list_like,
    is_object_dtype,
    is_scalar,
    is_timedelta64_dtype,
    needs_i8_conversion,
)
from pandas.core.dtypes.dtypes import CategoricalDtype
from pandas.core.dtypes.generic import ABCIndexClass, ABCSeries, ABCCategoricalIndex
from pandas.core.dtypes.missing import is_valid_nat_for_dtype, isna, notna

from pandas.core import ops
from pandas.core.accessor import PandasDelegate, delegate_names
import pandas.core.algorithms as algorithms
from pandas.core.algorithms import factorize, get_data_algo, take_1d, unique1d
from pandas.core.arrays._mixins import NDArrayBackedExtensionArray
from pandas.core.base import ExtensionArray, NoNewAttributesMixin, PandasObject
import pandas.core.common as com
from pandas.core.construction import array, extract_array, sanitize_array
from pandas.core.indexers import deprecate_ndim_indexing
from pandas.core.missing import interpolate_2d
from pandas.core.ops.common import unpack_zerodim_and_defer
from pandas.core.sorting import nargsort
from pandas.core.strings.object_array import ObjectStringArrayMixin

from pandas.io.formats import console

from pandas.core.arrays.categorical import _get_codes_for_values
from pandas.core.arrays.categorical import recode_for_categories
from pandas.core.tools.numeric import to_numeric