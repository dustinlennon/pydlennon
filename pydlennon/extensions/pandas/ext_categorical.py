
print("[module] ext_categorical.py [{0}]".format(__name__))

try:
    import IPython
    ipy = IPython.get_ipython()
    if ipy:
        if  not 'autoreload' in ipy.magics_manager.shell.extension_manager.loaded:
            ipy.run_line_magic("load_ext", "autoreload")
            ipy.run_line_magic("autoreload","2")
except ModuleNotFoundError:
    pass


import numpy as np
import logging

import re
import io

import pandas as pd
from pydlennon.patterns.instrumented import Instrumented
import pydlennon.extensions.pandas.util as util
import pydlennon.extensions.pandas as xpd

from pydlennon.extensions.pandas.instr_categorical import ICategoricalDtype, ICategorical


# ---------------------------------------------------------------------------------

@Instrumented()
class ExtCategoricalDtype(ICategoricalDtype):
    name    = "ext_category"

    def __repr__(self):
        s = self._repr()
        return "Ext{0}".format(s)


# ---------------------------------------------------------------------------------

@Instrumented()
class ExtCategorical(ICategorical):
    _dtype  = ExtCategoricalDtype(ordered=False)
    _typ    = "ext_categorical"


# ---------------------------------------------------------------------------------

xcd_gender = ExtCategoricalDtype((1,2))
xcd_race   = ExtCategoricalDtype((1,2))

# ---------------------------------------------------------------------------------

if __name__ == "__main__":
    # See tests/extensions/test_ext_categorical.py for usage

    print("[script] ext_categorical.py [{0}]".format(__name__))

    import numpy as np
    import pandas as pd

    import logging
    logging.basicConfig(level=logging.INFO)

    gds = util.gender_data_s
    gdi = [int(i) for i in gds]

    c0  = ExtCategorical._from_sequence(gds)
    c1  = ExtCategorical._from_sequence(gdi, dtype=xcd_gender)

    kw = {
        'dtype' : {
            'gender' : xcd_gender,
            'race'   : xcd_race
        },
        'usecols' : ['record_id', 'gender', 'race']
    }
    df  = util._read_csv(**kw)
    df.loc[19644, 'race'] = np.nan
