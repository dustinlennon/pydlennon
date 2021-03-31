import re
import unittest
import logging

from pydlennon.patterns.instrumented import Instrumented

class InstrumentedTestCase(unittest.TestCase):

    def setUp(self):
        class Base(object):
            def __init__(self):
                pass

            @staticmethod
            def bs():
                pass

            @classmethod
            def bc(cls):
                pass

            @property
            def bp(self):
                pass

            def bm(self):
                pass

        class Derived(Base):
            @staticmethod
            def ds():
                pass

            @classmethod
            def dc(cls):
                pass

            @property
            def dp(self):
                pass

            def dm(self):
                pass
        
        self.Base = Base
        self.Derived = Derived


        # logging.basicConfig(level=logging.DEBUG)
        # self.logger = logging.getLogger()


    def test_decorator_on_definition(self):
        Base = self.Base
        Derived = self.Derived

        with self.assertLogs("pydlennon.patterns.instrumented.Foo", level='DEBUG') as cm:
            @Instrumented()
            class Foo(Derived):
                pass

        dtypes = {
            "__repr__": "types.WrapperDescriptorType",
            "__hash__": "types.WrapperDescriptorType",
            "__str__": "types.WrapperDescriptorType",
            "__getattribute__": "types.WrapperDescriptorType",
            "__setattr__": "types.WrapperDescriptorType",
            "__delattr__": "types.WrapperDescriptorType",
            "__lt__": "types.WrapperDescriptorType",
            "__le__": "types.WrapperDescriptorType",
            "__eq__": "types.WrapperDescriptorType",
            "__ne__": "types.WrapperDescriptorType",
            "__gt__": "types.WrapperDescriptorType",
            "__ge__": "types.WrapperDescriptorType",
            "__init__": "types.FunctionType",
            "__new__": "types.BuiltinMethodType",
            "__reduce_ex__": "types.MethodDescriptorType",
            "__reduce__": "types.MethodDescriptorType",
            "__subclasshook__": "types.ClassMethodDescriptorType",
            "__init_subclass__": "types.ClassMethodDescriptorType",
            "__format__": "types.MethodDescriptorType",
            "__sizeof__": "types.MethodDescriptorType",
            "__dir__": "types.MethodDescriptorType",
            "__class__": "types.GetSetDescriptorType",
            "__doc__": "NoneType",
            "__module__": "string",
            "bs": "staticmethod",
            "bc": "classmethod",
            "bp": "property",
            "bm": "types.FunctionType",
            "__dict__": "types.GetSetDescriptorType",
            "__weakref__": "types.GetSetDescriptorType",
            "ds": "staticmethod",
            "dc": "classmethod",
            "dp": "property",
            "dm": "types.FunctionType",
            "_logger": "---"
        }


        for l in cm.output:
            k,v = re.sub(r"^DEBUG:pydlennon.patterns.instrumented.Foo:", "", l).split()
            self.assertTrue(k in dtypes)
            self.assertTrue(dtypes[k] == v)
            dtypes.pop(k)

        self.assertTrue( len(dtypes) == 0 )


    def test_instrumentation(self):
        Base = self.Base
        Derived = self.Derived

        @Instrumented()
        class Foo(Derived):
            pass

        # class instrumentation
        with self.assertLogs("pydlennon.patterns.instrumented.Foo", level='INFO') as cm:
            Foo.bs()
            Foo.bc()
            Foo.bp
            try:
                Foo.bm()
            except TypeError:
                pass
            Foo.ds()
            Foo.dc()
            Foo.dp
            try:
                Foo.dm()
            except TypeError:
                pass

        self.assertEqual(cm.output, [
            "INFO:pydlennon.patterns.instrumented.Foo:[staticmethod] bs",
            "INFO:pydlennon.patterns.instrumented.Foo:[classmethod] bc",
            "INFO:pydlennon.patterns.instrumented.Foo:[property] bp",
            "INFO:pydlennon.patterns.instrumented.Foo:[instance] bm",
            "INFO:pydlennon.patterns.instrumented.Foo:[staticmethod] ds",
            "INFO:pydlennon.patterns.instrumented.Foo:[classmethod] dc",
            "INFO:pydlennon.patterns.instrumented.Foo:[property] dp",
            "INFO:pydlennon.patterns.instrumented.Foo:[instance] dm",
        ])


        # instance instrumentation
        with self.assertLogs("pydlennon.patterns.instrumented.Foo", level='INFO') as cm:
            foo = Foo()
            foo.bs()
            foo.bc()
            foo.bp
            foo.bm()
            foo.ds()
            foo.dc()
            foo.dp
            foo.dm()

        self.assertEqual(cm.output, [
            "INFO:pydlennon.patterns.instrumented.Foo:[instance] __init__",
            "INFO:pydlennon.patterns.instrumented.Foo:[staticmethod] bs",
            "INFO:pydlennon.patterns.instrumented.Foo:[classmethod] bc",
            "INFO:pydlennon.patterns.instrumented.Foo:[property] bp",
            "INFO:pydlennon.patterns.instrumented.Foo:[instance] bm",
            "INFO:pydlennon.patterns.instrumented.Foo:[staticmethod] ds",
            "INFO:pydlennon.patterns.instrumented.Foo:[classmethod] dc",
            "INFO:pydlennon.patterns.instrumented.Foo:[property] dp",
            "INFO:pydlennon.patterns.instrumented.Foo:[instance] dm"
        ])
