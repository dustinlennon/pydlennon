
import warnings
import logging
import functools 
import types

# ------------------------------------------------------------------------------------

class ForwardingDescriptor(object):
    """
    A forwarding descriptor.  Currently, we require that this be be instantiated before 
    an instance of the delegate object is available.  

    Args:
        typ(type):              The type of the descriptor.
        delegate_name(str):     The attribute name of the descriptor instance in the container object
        attr_name(str):         The name of the attribute to forward.  A warning is generated if the 
                                delegate does not have an attribute with this name.
    """

    def __init__(self, typ, delegate_name, attr_name, logger):
        if not hasattr(typ, attr_name):
            msg = "The delegate type '{0}' does not provide attribute '{1}'.".format(typ.__name__, attr_name)
            logger.warning(msg)

        self._type              = typ
        self._delegate_name     = delegate_name
        self._attr_name         = attr_name
        self._logger            = logger

    def _log(self, bound, descriptor):
        msg_template = "{typename}<{bound}>.{attr_name}<{descriptor}>"
        msg = msg_template.format(
                typename    = self._type.__name__,
                bound       = bound,
                attr_name   = self._attr_name,
                descriptor  = descriptor
            )
        self._logger.info(msg)

    def __get__(self, instance, owner=None):
        if instance is None:  
            self._log("class", "getter")
            return getattr(self._type, self._attr_name)
        else:
            self._log("instance", "getter")
            delegate_instance = getattr(instance, self._delegate_name)
            return getattr(delegate_instance, self._attr_name)

    def __set__(self, instance, value):
        self._log("instance", "setter")

        delegate_instance   = getattr(instance, self._delegate_name)

        # preserve context of delegate when setting methods
        if isinstance(value, types.MethodType):
            if isinstance(value.__self__, type):
                value = value.__func__.__get__( type(delegate_instance) )
            else:
                value = value.__func__.__get__( delegate_instance )

        return setattr(delegate_instance, self._attr_name, value)

# ------------------------------------------------------------------------------------

class Proxy(object):
    """
    A decorator class that implements the proxy pattern.  It forwards to a delegate 
    by manipulating the descriptors.  

    Args:

        delegate_name (str):    The attribute name of the delegate instance
        delegate_type (str):    The type of the delegate object
        delegate_attrs (str):   The list of attribute names to be forwarded
    """
    def __init__(self, delegate_name, delegate_type, delegate_attrs, logging_level=logging.ERROR):
        self._delegate_name     = delegate_name
        self._delegate_type     = delegate_type
        self._delegate_typename = "{0}_type".format(delegate_name)
        self._delegate_attrs    = delegate_attrs
        self._logging_level     = logging_level

    # def _logger(self, klass):
    #     logger_id = "{0}.{1}".format(__name__, klass.__name__)
    #     logger = logging.getLogger( logger_id ) 
    #     return logger

    def _set_logger(self, klass):
        logger_id = "{0}.{1}".format(__name__, klass.__name__)
        logger = logging.getLogger( logger_id ) 
        logger.setLevel( self._logging_level)
        setattr(klass, "_logger", logger)
        return logger


    def __call__(self, klass):
        # Add the delegate type to the class
        setattr(klass, self._delegate_typename, self._delegate_type)

        # Add the logger to the class
        logger = self._set_logger( klass )

        # Add a descriptor for each delegate attribute to the class
        for attr in self._delegate_attrs:
            if hasattr(klass, attr):
                msg = "Overwriting an existing attribute '{0}'.".format(attr)
                logger.warning(msg)

            descriptor = ForwardingDescriptor(self._delegate_type, self._delegate_name, attr, logger)
            setattr(klass, attr, descriptor)

        # Rewrite the __init__ method to assert an instance of the delegate type exists 
        # in each instance of the class
        try:
            delegated = klass.__init__._wrapped
        except AttributeError:
            self._wrap_init(klass)

        return klass

    def _wrap_init(self, klass):
        var_name        = self._delegate_name
        var_type        = self._delegate_type
        var_typename    = ".".join([self._delegate_type.__module__, self._delegate_type.__name__])

        msg    =    "The Proxy decorator requires that {decorated_typename}.__init__ " \
                    "creates an instance variable of type '{delegate_typename}' and " \
                    "named '{delegate_name}'.".format(
                        decorated_typename  = klass.__name__,
                        delegate_typename   = var_typename,
                        delegate_name       = self._delegate_name
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
        setattr(klass, '__init__', wrapped_init)

        return wrapped_init

# ------------------------------------------------------------------------------------

if __name__ == "__main__":
    # See tests/patterns/test_proxy.py for usage
    pass
