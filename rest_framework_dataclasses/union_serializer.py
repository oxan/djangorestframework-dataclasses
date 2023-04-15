from __future__ import annotations

import inspect
from typing import Optional

from rest_framework import serializers
from rest_framework.fields import empty

try:
    from rest_polymorphic.serializers import PolymorphicSerializer
except ImportError:
    raise ImportError("In order to use union feature you need to install 'django-rest-polymorphic'."
                      "You can do it by running 'pip install djangorestframework-dataclasses[union]'")


class InlinePolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = None
    resource_type_field_name = "resourcetype"

    class Meta:
        ref_name: Optional[str] = None

    """
    This class utlizes PolymorphicSerializer from rest_polymorphic packageto support
    any class object (not limited to django models).

    Creating PolymorphicSerializer requires declaring a new class derived from it with "model_serializer_mapping"
    classvar.
    We could create dynamically new class derived from PolymorphicSerializer with "model_serializer_mapping" classvar,
    but in case that we have 2 classes with the same name (for example, same union in two different serializer)
    drf-spectacular warns that there is a conflict (2 different classes with the same name).
    In order to avoid this warning we create new class that let us get the "model_serializer_mapping"
    classvar (and few others classvars) from the constructor and actually make them instance members.
    """

    def __new__(cls, *args, **kwargs):
        return serializers.Serializer.__new__(cls, *args, **kwargs)

    def __init__(
        self,
        dataclass_serializer_mapping: Optional[dict] = None,
        resource_type_field_name: Optional[str] = None,
        ref_name: Optional[str] = None,
        *args,
        **kwargs,
    ):
        self.model_serializer_mapping = dataclass_serializer_mapping or self.model_serializer_mapping
        if self.model_serializer_mapping is None:
            raise ValueError("model_serializer_mapping is required")
        self.resource_type_field_name = resource_type_field_name or self.resource_type_field_name
        if self.resource_type_field_name is None:
            raise ValueError("resource_type_field_name is required")
        self.Meta.ref_name = ref_name or self.Meta.ref_name
        super().__init__(*args, **kwargs)

    def run_validation(self, data=empty):
        """
        The base class implementation of run_validation() relies on the fact that the validated_data will be a dict
        but in our case it can be a dataclass instance.
        """
        if self.partial and self.instance:
            serializer = self._get_serializer_from_model_or_instance(self.instance)
        else:
            resource_type = self._get_resource_type_from_mapping(data)
            serializer = self._get_serializer_from_resource_type(resource_type)

        validated_data = serializer.run_validation(data)
        return validated_data

    def to_resource_type(self, model_or_instance):
        return (
            model_or_instance.__name__ if inspect.isclass(model_or_instance) else model_or_instance.__class__.__name__
        )

    def _get_serializer_from_model_or_instance(self, model_or_instance):
        if self.model_serializer_mapping is None:
            raise ValueError("model_serializer_mapping is required")
        return self.model_serializer_mapping[
            model_or_instance if inspect.isclass(model_or_instance) else model_or_instance.__class__
        ]
