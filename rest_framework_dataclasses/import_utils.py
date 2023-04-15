from typing import Optional


def import_polymorphic_serializer(raise_error: bool = True) -> Optional[object]:
    try:
        from rest_polymorphic.serializers import PolymorphicSerializer
        return PolymorphicSerializer
    except ImportError:
        if raise_error:
            raise ImportError("In order to use union feature you need to install 'django-rest-polymorphic'."
                              "You can do it by running 'pip install djangorestframework-dataclasses[union]'")
    return None
