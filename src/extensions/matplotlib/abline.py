
import matplotlib
from matplotlib.pyplot import gca

class LineAb(matplotlib.lines._AxLine):
    def __init__(self, intercept, slope, *args, **kw):
        super().__init__([0,1], [intercept,intercept+slope], *args, **kw)

def _abline(self, intercept, slope, **kwargs):
    line = LineAb(intercept, slope, **kwargs)
    self._set_artist_props(line)
    if line.get_clip_path() is None:
        line.set_clip_path(self.patch)
    if not line.get_label():
        line.set_label(f"_line{len(self.lines)}")
    self.lines.append(line)
    line._remove_method = self.lines.remove
    
    self._request_autoscale_view()
    return line

setattr(matplotlib.axes.Subplot, 'abline', _abline)


# setattr(matplotlib.pyplot, 'abline', abline)
# def abline(intercept, slope, **kwargs):
#     return gca().abline(intercept, slope, **kwargs)
