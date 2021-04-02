
import logging
import types


# -----------------------------------------------------------------------------

class InstrumentedDescriptor(object):

    def __init__(self, klass, key, attr, logger):
        self._klass     = klass
        self._key       = key
        self._attr      = attr
        self._type      = type(attr)
        self._logger    = logger


    def _log(self, prefix):
        msg_template = "[{prefix}] {attr_name}"
        msg = msg_template.format(
                attr_name   = self._key,
                prefix      = prefix
            )
        self._logger.info(msg)

# -----------------------------------------------------------------------------

class StaticmethodDescriptor(InstrumentedDescriptor):
    def __get__(self, instance, owner=None):
        self._log("staticmethod")
        return self._attr.__get__(None, self._klass)

# -----------------------------------------------------------------------------

class ClassmethodDescriptor(InstrumentedDescriptor):
    def __get__(self, instance, owner=None):
        self._log("classmethod")
        return self._attr.__get__(None, self._klass)

# -----------------------------------------------------------------------------

class InstancemethodDescriptor(InstrumentedDescriptor):
    def __get__(self, instance, owner=None):
        self._log("instance")
        return self._attr.__get__(instance, self._klass)

# -----------------------------------------------------------------------------

class PropertyDescriptor(InstrumentedDescriptor):
    def __get__(self, instance, owner=None):
        self._log("property")
        return self._attr.__get__(instance, self._klass)

# -----------------------------------------------------------------------------

class Instrumented(object):

    instrumentable = [
        staticmethod, 
        classmethod, 
        property, 
        types.FunctionType
    ]

    def __init__(self, include = [], exclude=[]):
        self._instrument = set( self.instrumentable ).difference( exclude )

        if len(include) > 0:
            self._instrument = set( include ).intersection( self._instrument )

    def _set_logger(self, klass):
        logger_id = "{0}.{1}".format(__name__, klass.__name__)
        logger = logging.getLogger( logger_id ) 
        setattr(klass, "_logger", logger)
        return logger

    def __call__(self, klass):
        # Add the logger to the class
        logger = self._set_logger( klass )

        # Construct a "full mro" __dict__ of attributes 
        d = {}
        for T in klass.__mro__[::-1]:
            d.update( T.__dict__ )

        # Loop over the discovered attributes and create appropriate descriptors
        for k,attr in d.items():

            descriptor  = None

            fmt = lambda k,v: "{0:20} {1}".format(k,v)
            if isinstance(attr, staticmethod):
                logger.debug( fmt(k, "staticmethod") )
                if staticmethod in self._instrument:
                    descriptor = StaticmethodDescriptor(klass, k, attr, logger)

            elif isinstance(attr, classmethod):
                logger.debug( fmt(k, "classmethod") )
                if classmethod in self._instrument:
                    descriptor = ClassmethodDescriptor(klass, k, attr, logger)
            
            elif isinstance(attr, property):
                logger.debug( fmt(k, "property") )
                if property in self._instrument:
                    descriptor = PropertyDescriptor(klass, k, attr, logger)
            
            elif isinstance(attr, types.FunctionType):
                logger.debug( fmt(k, "types.FunctionType") )
                if types.FunctionType in self._instrument:
                    descriptor = InstancemethodDescriptor(klass, k, attr, logger)

            elif isinstance(attr, types.BuiltinMethodType):
                logger.debug( fmt(k, "types.BuiltinMethodType") )

            elif isinstance(attr, types.MethodType):
                logger.debug( fmt(k, "types.MethodType") )

            elif isinstance(attr, types.BuiltinFunctionType):
                logger.debug( fmt(k, "types.BuiltinFunctionType") )

            elif isinstance(attr, types.MethodWrapperType):
                logger.debug( fmt(k, "types.MethodWrapperType") )

            elif isinstance(attr, types.WrapperDescriptorType):
                logger.debug( fmt(k, "types.WrapperDescriptorType") )

            elif isinstance(attr, types.MethodDescriptorType):
                logger.debug( fmt(k, "types.MethodDescriptorType") )

            elif isinstance(attr, types.ClassMethodDescriptorType):
                logger.debug( fmt(k, "types.ClassMethodDescriptorType") )

            elif isinstance(attr, types.GetSetDescriptorType):
                logger.debug( fmt(k, "types.GetSetDescriptorType") )

            elif isinstance(attr, types.ModuleType):
                logger.debug( fmt(k, "types.ModuleType") )

            elif isinstance(attr, str):
                logger.debug( fmt(k, "string") )

            elif isinstance(attr, type(None)):
                logger.debug( fmt(k, "NoneType") )

            else:
                logger.debug( fmt(k, type(attr)) )

            if not descriptor is None:
                setattr(klass, k, descriptor)
            

        klass._instrumented = True
        return klass


if __name__ == '__main__':
    # See tests/patterns/instrumented.py for usage
    pass