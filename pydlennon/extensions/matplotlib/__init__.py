import matplotlib

from .abline import _abline
setattr(matplotlib.axes.Subplot, 'abline', _abline)
