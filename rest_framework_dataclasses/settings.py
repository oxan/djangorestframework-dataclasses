from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework_dataclasses import serializers

DEFAULTS = {
    'DEFAULT_DATACLASS_SERIALIZER': serializers.DataclassSerializer
}

IMPORT_STRINGS = [
    'DEFAULT_DATACLASS_SERIALIZER'
]


class DataclassSerializerSettings:
    def __init__(self, settings_key, defaults):
        self.settings_key = settings_key
        self.defaults = defaults

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid dataclass serializer setting '{attr}' accessed.")

        user_settings = getattr(settings, self.settings_key, {})
        value = user_settings.get(attr, self.defaults[attr])
        if attr in IMPORT_STRINGS and isinstance(value, str):
            value = import_string(value)
        return value


dataclass_serializer_settings = DataclassSerializerSettings('DATACLASS_SERIALIZER', DEFAULTS)
