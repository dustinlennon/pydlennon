import numpy as np

from patsy import ContrastMatrix, EvalFactor, LookupFactor


"""

    By default, Patsy removes columns that introduce rank-deficiencies.

    FullRankOneHot overrides this behavior.


"""

class FullRankOneHot(object):
    def __init__(self, reference=0):
        self.reference = reference

    def code_with_intercept(self, levels):
        return ContrastMatrix(np.eye(len(levels)),
                              ["[I.%s]" % (level,) for level in levels])

    def code_without_intercept(self, levels):
        return self.code_with_intercept(levels)


"""

    Define a mixin to override the default name method.  This utilizes a 
    method-chainable setter.

"""
class RenameableMixin(object):
    def set_name(self, name):
        self._name = name
        return self

    def name(self):
        return self._name

class LookupFactorRenamed(RenameableMixin, LookupFactor):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._name = LookupFactor.name(self)

class EvalFactorRenamed(RenameableMixin, EvalFactor):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._name = EvalFactor.name(self)


# ----

if __name__ == '__main__':
    import os
    import pandas as pd

    import extensions.patsy
    import common

    from patsy import ModelDesc, Term, dmatrix

    datafile = os.path.join(common.data_dir, "child.iq", 'kidiq.csv')

    kw = {
        'dtype' : {
            'mom_hs'    : 'category', 
            'mom_work'  : 'category', 
        }
    }
    df = pd.read_csv(datafile, **kw)


    """
        Create a ModelDesc object capable of displaying readable column names.  Compare 
        with:

            Xu = dmatrix(" ~ mom_hs + C(mom_work,extensions.patsy.FullRankOneHot)", data=df, return_type='dataframe')

    """
    factors = [
        extensions.patsy.LookupFactor('mom_hs'),
        extensions.patsy.EvalFactorRenamed('C(mom_work,extensions.patsy.FullRankOneHot)').set_name('mom_work')
    ]    
    terms = [Term([])] + [ Term([f]) for f in factors ]
    desc = ModelDesc([], terms)

    X = dmatrix(desc, df, return_type='dataframe')


