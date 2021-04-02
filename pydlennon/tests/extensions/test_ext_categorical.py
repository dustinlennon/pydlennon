
import unittest
import pandas as pd
import io

from pydlennon.extensions.pandas.ext_categorical import ExtCategoricalDtype, ExtCategorical


_testdata = """
,gender,ideo,partyid3,race
19641,1.0,,1.0,1.0
19642,2.0,,3.0,1.0
19643,2.0,,3.0,
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


class ExtCategoricalTestCase(unittest.TestCase):

    def setUp(self):
        def _read_csv(**_kw):
            fp = io.StringIO( _testdata )
            kw = {
                'index_col' : 'record_id',
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

        self.xcdtype_race   =   ExtCategoricalDtype( [
                                    (1, 'white'),
                                    (2, 'black'),
                                    (3, 'other')
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
        self.assertEqual(self.xcdtype_gender._ext, [(1,2),('male','female')] )
        self.assertEqual(repr(self.xcdtype_gender), "ExtCategoricalDtype(categories=[1, 2], ordered=False)")

    # ----

    def test_xcdtype_init_ordered(self):
        self.assertEqual(repr(self.xcdtype_educ), "ExtCategoricalDtype(categories=[1, 2, 3, 4], ordered=True)")

    # ----

    def test_series_from_sequence(self):
        xc  = ExtCategorical._from_sequence_of_strings(self.gender_data_s, dtype=self.xcdtype_gender)
        s   = pd.Series(xc)
        self.assertEqual(repr(s), u"0    1\n1    1\n2    2\n3    2\n4    1\n5    2\ndtype: ext_category")


        xc  = ExtCategorical._from_sequence_of_strings(self.gender_data_i, dtype=self.xcdtype_gender)
        s   = pd.Series(xc)
        self.assertEqual(repr(s), u"0    1\n1    1\n2    2\n3    2\n4    1\n5    2\ndtype: ext_category")

    # ----

    def test_create_from_series(self):
        s   = pd.Series(self.gender_data_i, dtype=self.xcdtype_gender)
        self.assertEqual(repr(s), u"0    1\n1    1\n2    2\n3    2\n4    1\n5    2\ndtype: ext_category")

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
                                     'dtype: ext_category' )

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
        self.assertEqual(repr(s),  u"record_id\n" \
                                    "19641      male\n" \
                                    "19642    female\n" \
                                    "19643    female\n" \
                                    "19644    female\n" \
                                    "19645    female\n" \
                                    "19646    female\n" \
                                    "19647      male\n" \
                                    "19648    female\n" \
                                    "19649      male\n" \
                                    "19650      male\n" \
                                    "19651    female\n" \
                                    "19652    female\n" \
                                    "dtype: ext_category")
    # ----

    def test_dropna(self):
        kw = {
            'dtype' : {
                'gender' : self.xcdtype_gender,
                'race'   : self.xcdtype_race
            },
            'usecols' : ['record_id', 'gender', 'race']
        }
        df          = self.loader(**kw)
        df_clean    = df.dropna()
        dtypes      = df_clean.dtypes

        gender_coded    = df_clean.gender
        gender          = gender_coded.xcat.relevel(1)

        race_coded      = df_clean.race
        race            = race_coded.xcat.relevel(1)


        self.assertTrue( (dtypes == 'ext_category').all() )
        self.assertListEqual( gender_coded.unique().to_list(),  [1,2] ) 
        self.assertListEqual( gender.unique().to_list(), ['male', 'female'])
        self.assertListEqual( race.unique().to_list(), ['white', 'black'])
        self.assertListEqual( race.dtype.categories.to_list(), ['white', 'black','other'])


    # ----

    def test_assign_to_dataframe(self):
        kw = {
            'dtype' : {
                'gender' : self.xcdtype_gender,
                'race'   : self.xcdtype_race
            },
            'usecols' : ['record_id', 'gender', 'race']
        }
        df  = self.loader(**kw)
        df.loc[:,'xx'] = df.race.xcat.relevel(1)

        self.assertEqual( 
            repr(df.xx.head()),
            u"record_id\n" \
             "19641    white\n" \
             "19642    white\n" \
             "19643      NaN\n" \
             "19644    white\n" \
             "19645    black\n" \
             "Name: xx, dtype: ext_category"
        )



    # ----

    def test_zero_count_behavior(self):
        kw = {
            'dtype' : {
                'gender' : self.xcdtype_gender,
                'race'   : self.xcdtype_race
            },
            'usecols' : ['record_id', 'gender', 'race']
        }
        df  = self.loader(**kw)

        race        = df.race.xcat.relevel(1)
        zcv         = race.value_counts().reset_index().values.tolist()

        self.assertListEqual( zcv, [['white', 8], ['black', 3], ['other', 0]] )



# -----------------------------------------------------------------------------

if __name__ == '__main__':
    """
    # Run from tests subdirectory
    $ python3 -m unittest discover -b -s ..

    # OR, from package root directory
    $ python3 -m unittest discover
    """
    unittest.main()