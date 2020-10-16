from rest_framework.fields import DecimalField


class DefaultDecimalField(DecimalField):
    def __init__(self, **kwargs):
        if 'max_digits' not in kwargs:
            kwargs['max_digits'] = None
        if 'decimal_places' not in kwargs:
            # Maybe this should be configurable, but it doesn't seem that useful. File an issue if you want it to.
            kwargs['decimal_places'] = 2

        super(DefaultDecimalField, self).__init__(**kwargs)
