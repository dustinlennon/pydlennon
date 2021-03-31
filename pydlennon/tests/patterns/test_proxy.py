import unittest
import logging
import sys

from pydlennon.patterns.proxy import Proxy

class _NamedMixin(object):
    @property
    def __name__(self):        
        return type(self).__name__.lower()


class ProxyTestCase(unittest.TestCase):

    def setUp(self):

        class Foo(_NamedMixin):
            @classmethod
            def c(cls):
                return "Foo.c"

            def f(self):
                return "foo.f"

            def g(self):
                return "foo.g"

        @Proxy("foo", Foo, ['c', 'g'])
        class Bar(_NamedMixin):
            def __init__(self):
                self.foo = Foo()

        @Proxy("bar", Bar, ['c', 'g'])
        class Qux(_NamedMixin):
            def __init__(self):
                self.bar = Bar()

        @Proxy("qux", Qux, ['c', 'g'])
        class Xyzzy(_NamedMixin):
            def __init__(self):
                self.qux = Qux()

        self.Foo    = Foo
        self.Bar    = Bar
        self.Qux    = Qux
        self.Xyzzy  = Xyzzy

    # ----

    def test_init_creates_delegate_instance(self):

        Foo = self.Foo

        @Proxy("foo", Foo, [], logging_level = logging.INFO)
        class FooProxy(object):
            def __init__(self):
                pass

        with self.assertRaises(AttributeError) as error:
            foo_proxy = FooProxy()


    # ----

    def test_decorator_warnings(self):

        with self.assertLogs("pydlennon.patterns.proxy.FooProxy", level='WARNING') as cm:

            @Proxy("foo", self.Foo, ['bar', "g"], logging_level = logging.WARNING)
            class FooProxy(object):
                def __init__(self):
                    self.foo = self.Foo()
                
                def g(self):
                    pass

        self.assertEqual(cm.output, [
            "WARNING:pydlennon.patterns.proxy.FooProxy:The delegate type 'Foo' does not provide attribute 'bar'.",
            "WARNING:pydlennon.patterns.proxy.FooProxy:Overwriting an existing attribute 'g'."
        ])

    # ----

    def test_delegator_verbosity(self):

        Foo = self.Foo
        
        @Proxy("foo", Foo, ['c', "g"], logging_level = logging.INFO)
        class FooProxy(object):
            def __init__(self):
                self.foo = Foo()
            
            def f(self):
                return "FooProxy.f"
                

        foo_proxy = FooProxy()

        with self.assertLogs("pydlennon.patterns.proxy.FooProxy", level="INFO") as cm:

            self.assertEqual(FooProxy.c(), "Foo.c")
            self.assertEqual(foo_proxy.c(), "Foo.c")
            self.assertEqual(foo_proxy.g(), "foo.g")

        self.assertEqual(cm.output, [
            "INFO:pydlennon.patterns.proxy.FooProxy:Foo<class>.c<getter>",
            "INFO:pydlennon.patterns.proxy.FooProxy:Foo<instance>.c<getter>",
            "INFO:pydlennon.patterns.proxy.FooProxy:Foo<instance>.g<getter>"
        ])

    # ----

    def test_setter_context(self):
        Foo = self.Foo
        Bar = self.Bar

        bar = Bar()

        static_method   = lambda self: "{0}.{1}".format(42, self.__name__)
        class_method    = static_method.__get__(Bar)
        instance_method = static_method.__get__(bar)

        bar.g = instance_method
        bar.c = class_method

        self.assertEqual(bar.g.__self__, bar.foo)
        self.assertEqual(bar.c.__self__, Foo)

        self.assertEqual(bar.g(), "42.foo")
        self.assertEqual(bar.c(), "42.Foo")


    # ----

    def test_setter_recursion(self):

        Foo     = self.Foo
        Xyzzy   = self.Xyzzy
        
        xyzzy = Xyzzy()        

        static_method   = lambda self: "{0}.{1}".format(42, self.__name__)
        class_method    = static_method.__get__(Xyzzy)
        instance_method = static_method.__get__(xyzzy)

        xyzzy.c = class_method
        xyzzy.g = instance_method

        self.assertEqual(xyzzy.c.__self__, Foo)
        self.assertEqual(xyzzy.g.__self__, xyzzy.qux.bar.foo)

        self.assertEqual(xyzzy.g(), "42.foo")
        self.assertEqual(xyzzy.c(), "42.Foo")


# -----------------------------------------------------------------------------

if __name__ == '__main__':
    """
    # Run from tests subdirectory
    $ python3 -m unittest discover -b -s ..

    # OR, from package root directory
    $ python3 -m unittest discover
    """
    unittest.main()