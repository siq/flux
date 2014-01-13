from scheme.interpolation import interpolate_parameters
from spire.schema import *

__all__ = ('EmailTemplate',)

schema = Schema('flux')

class EmailTemplate(Model):
    """An email template."""

    class meta:
        schema = schema
        tablename = 'emailtemplate'

    id = Identifier()
    template = Text(nullable=False, unique=True)

    @classmethod
    def put(cls, session, template):
        session.begin_nested()
        try:
            instance = cls(template=template)
            session.add(instance)
            session.commit()
            return instance
        except IntegrityError:
            session.rollback()
            return session.query(cls).filter(cls.template==template).one()

    def evaluate(self, parameters):
        return interpolate_parameters(self.template, parameters)
