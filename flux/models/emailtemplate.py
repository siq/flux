from scheme.interpolation import interpolate_parameters
from scheme.util import recursive_merge
from spire.schema import *

__all__ = ('EmailTemplate',)

schema = Schema('flux')

class EmailTemplate(Model):
    """An email template."""

    class meta:
        constraints = [UniqueConstraint('template',
            name='email_template_unique')]
        schema = schema
        tablename = 'emailtemplate'

    id = Identifier()
    template = Text(nullable=False)

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

    def evaluate(self, parameters=None):
        params = {}
        if parameters:
            print 'ADRIAN TEST....................'
            print parameters
            recursive_merge(params, parameters)
        print 'ADRIAN TEST....................'
        print params
        return interpolate_parameters(self.template, params)