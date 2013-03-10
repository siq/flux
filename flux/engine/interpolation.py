

class Interpolator(dict):
    """A parameter interpolator."""

    def interpolate(self, field, subject):
        return field.interpolate(subject, self)

