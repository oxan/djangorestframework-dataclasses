from rest_framework.fields import DecimalField, ChoiceField


class DefaultDecimalField(DecimalField):
    def __init__(self, **kwargs):
        if 'max_digits' not in kwargs:
            kwargs['max_digits'] = None
        if 'decimal_places' not in kwargs:
            # Maybe this should be configurable, but it doesn't seem that useful. File an issue if you want it to.
            kwargs['decimal_places'] = 2

        super(DefaultDecimalField, self).__init__(**kwargs)


class EnumField(ChoiceField):
    def __init__(self, enum_class, by_name=False, **kwargs):
        self.enum_class = enum_class
        self.by_name = by_name
        if 'choices' not in kwargs:
            kwargs['choices'] = [(self.to_representation(member), member.name) for member in self.enum_class]

        super(EnumField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            if self.by_name:
                return self.enum_class[data]
            else:
                return self.enum_class(data)
        except (KeyError, ValueError):
            self.fail('invalid_choice', input=data)

    def to_representation(self, value):
        if self.by_name:
            return value.name
        else:
            return value.value
