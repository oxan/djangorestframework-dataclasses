1.3.0, 21 August 2023
---------------------
Breaking changes:

* The type annotations now require mypy 1.0 or higher to validate correctly.

Features & fixes:

* Create values for fields of non-``list`` or ``dict`` composite types (such as ``frozenset`` or ``OrderedDict``) as
  that type, instead of ``list`` or ``dict``.
* Allow overriding the field for specific composite types through the ``serializer_field_mapping`` dictionary.
* Don't set optional fields to ``rest_framework.fields.empty`` sentinel value when used in non-partial mode. This fixes
  occasional leaks of the sentinel into dataclasses returned to the user, for example when a ``DataclassSerializer`` was
  nested inside a regular serializer. Not setting, and later stripping, the sentinels also increases performance.
* Support dataclasses with fields that have ``init=False``.
* Support ``save()`` on serializers with ``many=True``.
* Support for fields with union types.
* Support nested serializers with ``source='*'``.
* Fix ``child_kwargs`` defined in dataclass field metadata (as opposed to ``extra_kwargs`` field on ``Meta`` subclass).

1.2.0, 18 November 2022
-----------------------
Features & fixes:

* Allow all types, including special forms such as unions, to have their field type overridden through the
  ``serializer_field_mapping`` dictionary.
* Also treat unions containing ``None`` as optional if they consist of three or more members. Previously this was only
  the case for unions with two members (i.e. only unions of a type with ``None`` were optional).
* Many added and fixed type hints.

1.1.1, 25 January 2022
----------------------
Features & fixes:

* Fix usage of PEP 585 generics with forward references (e.g. ``list["str"]``).
* Fix usage of ``allow_empty`` with ``many=True``.

1.1.0, 9 January 2022
---------------------
Features & fixes:

* Allow using the new ``X | None`` union syntax for specifying optional fields in Python 3.10+ (PEP 604).

1.0.0, 23 October 2021
----------------------
Features & fixes:

* Allow serialization of properties created using @property decorator.
* Allow dataclass types to be serialized by a type not inheriting from ``DataclassSerializer`` (usually a ``Field``).

0.10, 19 July 2021
------------------
Features & fixes:

* Fix ``EnumField`` compatibility with drf-yasg.

0.9, 18 April 2021
------------------
Breaking changes:

* The serializer field for dataclass fields that have a default value or default value factory, are now marked as
  optional (``required=False``).
* Marking dataclass fields with ``typing.Optional`` no longer causes the serializer fields to be optional (they will
  still be marked as nullable). In previous versions these fields would be optional, which broke if a field had no
  default value. Due to the previous change, the common case of fields marked with ``typing.Optional`` that had ``None``
  as a default value have no change in behaviour.
* Drop support for generic ``typing.Final`` type hints (without the type specified), as ``typing.Final`` was never
  supposed to be used in this way, and Python 3.10 will drop support for it.

Features & fixes:

* Support overriding serializer for a nested dataclass using ``serializer_field_mapping``.
* Support overriding serializer for all nested dataclasses using ``serializer_dataclass_field`` property.
* Support partial updates of nested dataclasses.
* Support bound type variables.
* Support field generation for enumerations.
* Support specifying serializer field configuration in dataclass field metadata.
* Fix value for non-specified optional fields in validated_data on serializers with ``many=True``.

0.8, 6 November 2020
--------------------
Breaking changes:

* The ``validated_data`` representation no longer contains the ``rest_framework.fields.empty`` sentinel value for
  unsupplied fields. This reverts the breaking change from v0.7.

Features & fixes:

* Don't install tests into distributed packages.

0.7, 23 October 2020
--------------------
Breaking changes:

* The ``validated_data`` representation now contains the ``rest_framework.fields.empty`` sentinel value for fields where
  no value was provided, instead of the default of the dataclass field. The value returned by ``save()`` is unchanged.
  This was necessary to support partial updates.

Features & fixes:

* Improved Python 3.9 compatibility.
* Support partial updates.
* Support standard collection generics (PEP 585).
* Support non-generic ``list`` and ``dict`` typehints.
* Support final fields (PEP 591).
* Support auto-generation for list or dictionaries of Any or variable type.
* Set default ``max_digits`` and ``decimal_places`` for ``DecimalField``.
* Improved error message when automatic field type deduction fails.

0.6, 17 April 2020
------------------
* Rewrite to ``save()`` implementation to finally fix all issues with nested serializers.
* Fix deserialization for fields using ``source`` option.
* Fix explicit specification of a method in the ``fields`` option.

0.5, 10 March 2020
------------------
* Make optional fields on the dataclass optional on the serializer as well.
* Fix (de-)serialization of dataclass lists specified with ``many=True``.
* Fix deserialization of nullable nested dataclasses.
* Raise error when field is both declared and is present in ``extra_kwargs``.
* Raise error when non-existing fields are included in ``fields`` option.
* Minor performance improvements.

0.4, 03 February 2020
---------------------
* Automatically recognize ``Literal``-typed fields (PEP 586).
* Fix deserialization of dataclasses inside dictionaries.
* Improve error message when encountering field with a special form type.

0.3, 31 December 2019
---------------------
* Automatically recognize UUID fields.
* Fix saving with nested dataclasses.

0.2, 18 September 2019
----------------------
* Support arbitrary nesting of dictionaries and lists.
* Support putting ``__all__`` magic option in ``fields`` option on Meta class.

0.1, 09 September 2019
----------------------
* Initial release.
