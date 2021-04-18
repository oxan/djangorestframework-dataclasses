0.9, 18 April 2021
------------------
Breaking changes:

* The serializer field for dataclass fields that have a default value or default value factory, are now marked as
  optional (``required=False``).
* Marking dataclass fields with ``typing.Optional`` no longer causes the serializer fields to be optional (they will
  still be marked as nullable). In previous versions these fields would be optional, which broke if a field had no
  default value. Due to the previous change, the common case of fields marked with ``typing.Optional`` that had ``None``
  as a default value have no change in behaviour.

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
