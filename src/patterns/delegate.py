
import warnings
import logging
import functools 
import types

# ------------------------------------------------------------------------------------

class DelegateDescriptor(object):

    msg_template = "{typename}<{bound}>.{attrname}<{descriptor}>"

    def __init__(self, typ, name, attrname, logger):
        if not hasattr(typ, attrname):
            msg = "The delegate type '{0}' does not provide attribute '{1}'.".format(typ.__name__, attrname)
            logger.warning(msg)

        self._type      = typ
        self._name      = name
        self._attrname   = attrname
        self._logger    = logger

    def _fill_template(self, bound, descriptor):
        return self.msg_template.format(
                typename    = self._type.__name__,
                bound       = bound,
                attrname    = self._attrname,
                descriptor  = descriptor
            )

    def __get__(self, instance, owner=None):
        if instance is None:            
            msg = self._fill_template( "class", "getter" )
            self._logger.info(msg) 

            return getattr(self._type, self._attrname)
        else:
            msg = self._fill_template( "instance", "getter" )
            self._logger.info(msg) 

            delegate_instance = getattr(instance, self._name)
            return getattr(delegate_instance, self._attrname)

    def __set__(self, instance, value):
        msg = self._fill_template( "instance", "setter" )
        self._logger.info(msg) 

        delegate_instance   = getattr(instance, self._name)

        # preserve context of delegate when setting methods
        if isinstance(value, types.MethodType):
            if isinstance(value.__self__, type):
                value = value.__func__.__get__( type(delegate_instance) )
            else:
                value = value.__func__.__get__( delegate_instance )

        return setattr(delegate_instance, self._attrname, value)

# ------------------------------------------------------------------------------------

class Delegate(object):
    def __init__(self, delegate_name, delegate_type, delegate_attrs, logging_level=logging.ERROR):
        self._delegate_name     = delegate_name
        self._delegate_type     = delegate_type
        self._delegate_typename = "{0}_type".format(delegate_name)
        self._delegate_attrs    = delegate_attrs
        self._logging_level     = logging_level


    def _logger(self, klass):
        logger_id = "{0}.{1}".format(__name__, klass.__name__)
        logger = logging.getLogger( logger_id ) 
        return logger

    def __call__(self, klass):
        # Add the delegate type to the class
        setattr(klass, self._delegate_typename, self._delegate_type)

        # Add the logger to the class
        logger = self._logger( klass )
        logger.setLevel( self._logging_level )
        setattr(klass, "_logger", logger)

        # Add a descriptor for each delegate attribute to the class
        for attr in self._delegate_attrs:
            if hasattr(klass, attr):
                msg = "Overwriting an existing attribute '{0}'.".format(attr)
                logger.warning(msg)

            descriptor = DelegateDescriptor(self._delegate_type, self._delegate_name, attr, logger)
            setattr(klass, attr, descriptor)

        # Rewrite the __init__ method to assert an instance of the delegate type exists 
        # in each instance of the class
        try:
            delegated = klass.__init__._wrapped
        except AttributeError:
            wrapped_init = self._wrap_init(klass)
            setattr(klass, '__init__', wrapped_init)

        return klass

    def _wrap_init(self, klass):
        var_name        = self._delegate_name
        var_type        = self._delegate_type
        var_typename    = ".".join([self._delegate_type.__module__, self._delegate_type.__name__])

        msg    =    "The Delegate decorator requires that {decorated_class}.__init__ " \
                    "creates an instance variable of type '{delegate_type}'' and " \
                    "named '{delegate_name}'.".format(
                        decorated_class = klass.__name__,
                        delegate_type = var_typename,
                        delegate_name = self._delegate_name
                    )

        __init__        = getattr(klass, "__init__")

        @functools.wraps(__init__)
        def wrapped_init(self, *args, **kw):
            __init__(self, *args, **kw)
            try:
                delegate = getattr(self, var_name)
            except AttributeError as e:
                self._logger.error(msg)
                raise AttributeError(msg) from e

            if not isinstance(delegate, var_type):
                self._logger.error(msg)
                raise TypeError(msg)

        setattr(wrapped_init, "_wrapped", True)
        return wrapped_init

# ------------------------------------------------------------------------------------

if __name__ == "__main__":

    import logging
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    class Foo(object):
        """
        The Foo docstring
        """

        @classmethod
        def c(cls):
            return "Foo.c"

        def f(self):
            return "foo.f"

        def g(self):
            return "foo.g"

    print("\n----\n")

    @Delegate("foo", Foo, ["bar", "c", "g"], logging_level = logging.INFO)
    class BrokenDelegator(object):
        def __init__(self):
            """
            BrokenDelegator.__init__ docstring
            """
            pass

        def f(self):
            return "delegator.f"

        def g(self):
            return "delegator.g"

    try:
        bd = BrokenDelegator()
    except AttributeError as e:
        pass

    @Delegate("foo", Foo, ["c", "g"])
    class WorkingDelegator(object):
        def __init__(self):
            """
            WorkingDelegator.__init__ docstring
            """
            self.foo = Foo()

        def f(self):
            return "working_delegator.f"

    print("\n----\n")

    @Delegate("foo", Foo, ["c", "g"], logging_level = logging.INFO)
    class VerboseDelegator(WorkingDelegator):
        pass

    print("\n----\n")

    foo = Foo()
    wd  = WorkingDelegator()

    print("Debug tracing:\n")
    vd  = VerboseDelegator()
    x = foo.c()
    print( "foo.c() : %s\n" % x )

    x = vd.c()
    print( "vd.c()  : %s\n" % x )

    x = vd.g()
    print( "vd.g()  : %s\n" % x )

    x = vd.f()
    print( "vd.f()  : %s\n" % x )

    # check that functions, class methods, and instance methods are correctly bound 
    # to the expected context
    sm = lambda self: 42
    cm = sm.__get__(WorkingDelegator)
    im = sm.__get__(wd)

    print("\n----\n")
    print("Setting a delegated attribute (g):")
    print("\nSTATICMETHOD")
    wd.g = sm
    print( "wd.g    : ", wd.g )

    print("\nCLASSMETHOD")
    wd.g = cm
    print( "wd.g    : ", wd.g )

    print("\nINSTANCEMETHOD")
    wd.g = im
    print( "wd.g    : ", wd.g )


    print("\n----\n")
    print("Setting an undelegated attribute (f):")
    print("\nSTATICMETHOD")
    wd.f = sm
    print( "wd.f    : ", wd.f )

    print("\nCLASSMETHOD")
    wd.f = cm
    print( "wd.f    : ", wd.f )

    print("\nINSTANCEMETHOD")
    wd.f = im
    print( "wd.f    : ", wd.f )
