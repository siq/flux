from scheme.util import recursive_merge

class Interpolator(dict):
    """A parameter interpolator."""

    def clone(self):
        return Interpolator(self)

    def interpolate(self, field, subject):
        return field.interpolate(subject, self)

    def merge(self, values):
        recursive_merge(self, values)
