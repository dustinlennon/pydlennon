
import unittest
import pandas as pd
import io

from extensions.pandas.ext_categorical import ExtCategoricalDtype, ExtCategorical


_testdata = """
,gender,ideo,partyid3,race
19641,1.0,,1.0,1.0
19642,2.0,,3.0,1.0
19643,2.0,,3.0,1.0
19644,2.0,,3.0,1.0
19645,2.0,,2.0,2.0
19646,2.0,,1.0,2.0
19647,1.0,,1.0,1.0
19648,2.0,,1.0,1.0
19649,1.0,,1.0,1.0
19650,1.0,,3.0,1.0
19651,2.0,,2.0,2.0
19652,2.0,,1.0,1.0
""".strip()


class ProxyTestCase(unittest.TestCase):

    def setUp(self):
        def _read_csv(**_kw):
            fp = io.StringIO( _testdata )
            kw = {
                'index_col' : 0,
                'header' : 0,
                'names' : [
                    'record_id',
                    'gender',
                    'ideo',
                    'partyid3',
                    'race'
                ],
            }

            kw.update(**_kw)
            df = pd.read_csv(fp, **kw)

            return df

        self.loader = _read_csv

        self.xcdtype_gender =   ExtCategoricalDtype( [
                                    (1, 'male'),
                                    (2, 'female')
                                ])

        self.xcdtype_educ =     ExtCategoricalDtype([
                                    (1, 'grade school'),
                                    (2, 'high school'),
                                    (3, 'some college'),
                                    (4, 'college or advanced degree')
                                ], ordered=True)


        self.gender_data_s =    ["1","1","2","2","1","2"]
        self.gender_data_i =    [1,1,2,2,1,2]
        self.educ_data_i   =    [2,3,3,1,2,4,3,2]


    # ----

    @unittest.skip
    def test_loader(self):
        df = self.loader()
        raise Exception(repr(df))

    # ----

    def test_xcdtype_init(self):
        self.assertEqual(repr(self.xcdtype_gender), "CategoricalDtype(categories=[1, 2], ordered=False)")

    # ----

    def test_xcdtype_init_ordered(self):
        self.assertEqual(repr(self.xcdtype_educ), "CategoricalDtype(categories=[1, 2, 3, 4], ordered=True)")

    # ----

    def test_series_from_sequence(self):
        xc  = ExtCategorical._from_sequence_of_strings(self.gender_data_s, dtype=self.xcdtype_gender)
        s   = pd.Series(xc)
        self.assertEqual(repr(s), u"0    1\n1    1\n2    2\n3    2\n4    1\n5    2\ndtype: wrapped_category")


        xc  = ExtCategorical._from_sequence_of_strings(self.gender_data_i, dtype=self.xcdtype_gender)
        s   = pd.Series(xc)
        self.assertEqual(repr(s), u"0    1\n1    1\n2    2\n3    2\n4    1\n5    2\ndtype: wrapped_category")

    # ----

    def test_create_from_series(self):
        s   = pd.Series(self.gender_data_i, dtype=self.xcdtype_gender)
        self.assertEqual(repr(s), u"0    1\n1    1\n2    2\n3    2\n4    1\n5    2\ndtype: wrapped_category")

    # ----

    def test_ordered(self):
        sex     = pd.Series(self.gender_data_i, dtype=self.xcdtype_gender)
        educ    = pd.Series(self.educ_data_i, dtype=self.xcdtype_educ)

        with self.assertRaises(TypeError):
            sex.min()

        self.assertEqual(educ.min(), 1)
        self.assertEqual(educ.max(), 4)

    # ----

    def test_xcat_relevel(self):
        educ    = pd.Series(self.educ_data_i, dtype=self.xcdtype_educ)
        s       = educ.xcat.relevel(1)

        self.assertEqual(type(s.dtype), ExtCategoricalDtype)

        self.assertEqual(repr(s),   u'0                   high school\n' \
                                     '1                  some college\n' \
                                     '2                  some college\n' \
                                     '3                  grade school\n' \
                                     '4                   high school\n' \
                                     '5    college or advanced degree\n' \
                                     '6                  some college\n' \
                                     '7                   high school\n' \
                                     'dtype: wrapped_category' )

    # ----

    def test_csv_import(self):
        kw = {
            'dtype' : {
                'gender' : self.xcdtype_gender
            }
        }
        df  = self.loader(**kw)

        self.assertEqual(type(df.gender.dtype), ExtCategoricalDtype)

        s = df.gender.xcat.relevel(1)
        self.assertEqual(repr(s),  u'0       male\n' \
                                    '1     female\n' \
                                    '2     female\n' \
                                    '3     female\n' \
                                    '4     female\n' \
                                    '5     female\n' \
                                    '6       male\n' \
                                    '7     female\n' \
                                    '8       male\n' \
                                    '9       male\n' \
                                    '10    female\n' \
                                    '11    female\n' \
                                    'dtype: wrapped_category')

