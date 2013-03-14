from scheme.interpolation import Interpolator as BaseInterpolator
from scheme.util import recursive_merge

base_interpolator = BaseInterpolator()

class Interpolator(dict):
    """A parameter interpolator."""

    def clone(self):
        return Interpolator(self)

    def evaluate(self, subject):
        return base_interpolator.evaluate(subject, self)

    def interpolate(self, field, subject):
        return field.interpolate(subject, self, base_interpolator)

    def merge(self, values):
        recursive_merge(self, values)
