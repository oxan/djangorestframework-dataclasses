0.6, 17 April 2020
------------------
* Rewrite to ``save()`` implementation to finally fix all issues with nested
  serializers.
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
* Automatically recognize ``Literal``-typed fields.
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