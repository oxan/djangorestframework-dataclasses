Dataclasses serializer
======================

A `dataclasses <https://docs.python.org/3/library/dataclasses.html>`__ serializer for the `Django REST Framework
<http://www.django-rest-framework.org/>`__.

.. image:: https://github.com/oxan/djangorestframework-dataclasses/workflows/CI/badge.svg
   :target: https://github.com/oxan/djangorestframework-dataclasses/actions?query=workflow%3ACI
.. image:: https://codecov.io/gh/oxan/djangorestframework-dataclasses/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/oxan/djangorestframework-dataclasses
.. image:: https://badge.fury.io/py/djangorestframework-dataclasses.svg
   :target: https://badge.fury.io/py/djangorestframework-dataclasses
.. image:: https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=success
   :target: https://github.com/sponsors/oxan

|

.. contents:: :local:

Requirements
------------

* Python (3.8+)
* Django (3.2+)
* Django REST Framework (3.11+)

These are the supported Python and package versions. Older versions will probably work as well, but aren't tested.

Installation
------------

::

    $ pip install djangorestframework-dataclasses

This package follows `semantic versioning`_. See `CHANGELOG`_ for breaking changes and new features, and `LICENSE`_ for
the complete license (BSD-3-clause).

.. _`semantic versioning`: https://semver.org/
.. _`CHANGELOG`: https://github.com/oxan/djangorestframework-dataclasses/blob/master/CHANGELOG.rst
.. _`LICENSE`: https://github.com/oxan/djangorestframework-dataclasses/blob/master/LICENSE

Basic usage
-----------

The package provides the ``DataclassSerializer`` serializer, defined in the ``rest_framework_dataclasses.serializers``
namespace.

.. code:: Python

    from rest_framework_dataclasses.serializers import DataclassSerializer

This serializer provides a shortcut that lets you automatically create a ``Serializer`` class with fields that
correspond to the fields on a dataclass. In usage, the ``DataclassSerializer`` is the same as a regular ``Serializer``
class, except that:

* It will automatically generate fields for you, based on the declaration in the dataclass.
* To make this possible it requires that a ``dataclass`` property is specified in the ``Meta`` subclass, with as value
  a dataclass that has type annotations.
* It includes default implementations of ``.create()`` and ``.update()``.

For example, define a dataclass as follows:

.. code:: Python

    @dataclass
    class Person:
        name: str
        email: str
        alive: bool
        gender: typing.Literal['male', 'female']
        birth_date: typing.Optional[datetime.date]
        phone: typing.List[str]
        movie_ratings: typing.Dict[str, int]

The serializer for this dataclass can now trivially be defined without having to duplicate all fields:

.. code:: Python

    class PersonSerializer(DataclassSerializer):
        class Meta:
            dataclass = Person

    # is equivalent to
    class PersonSerializer(Serializer):
        name = fields.CharField()
        email = fields.CharField()
        alive = fields.BooleanField()
        gender = fields.ChoiceField(choices=['male', 'female'])
        birth_date = fields.DateField(allow_null=True)
        phone = fields.ListField(child=fields.CharField())
        movie_ratings = fields.DictField(child=fields.IntegerField())

You can add extra fields or override default fields by declaring them explicitly on the class, just as you would for a
regular ``Serializer`` class. This allows to specify extra field options or change a field type.

.. code:: Python

    class PersonSerializer(Serializer):
        email = fields.EmailField()

        class Meta:
            dataclass = Person

Dataclass serializers behave in the same way and can be used in the same places as the built-in serializers from Django
REST Framework: you can retrieve the serialized representation using the ``.data`` property, and the deserialized
dataclass instance using the ``.validated_data`` property. Furthermore, the ``save()`` method is implemented to create
or update an existing dataclass instance. You can find more information on serializer usage in the
`Django REST Framework <https://www.django-rest-framework.org/api-guide/serializers/>`__ documentation.

Note that this usage pattern is very similar to that of the built-in ``ModelSerializer``. This is intentional, with the
whole API modelled after that of ``ModelSerializer``. Most features and behaviour known from ``ModelSerializer`` applies
to dataclass serializers as well.

Field mapping
-------------

Currently, automatic field generation is supported for the following types and their subclasses:

* ``str``, ``bool``, ``int`` and ``float``.
* ``date``, ``datetime``, ``time`` and ``timedelta`` from the ``datetime`` package.
* ``decimal.Decimal`` (``max_digits`` and ``decimal_places`` default to ``None`` and ``2`` respectively).
* ``uuid.UUID``
* ``enum.Enum`` (mapped to a ``EnumField``)
* ``typing.Iterable`` (including ``typing.List`` and `PEP 585`_-style generics such as ``list[int]``).
* ``typing.Mapping`` (including ``typing.Dict`` and `PEP 585`_-style generics such as ``dict[str, int]``).
* ``typing.Literal`` (mapped to a ``ChoiceField``).
* ``typing.Union`` (mapped to a ``UnionField``, including `PEP 604`_-style unions such as ``str | int``, see
  `UnionField`_ section below for more information).
* ``django.db.Model``

The serializer also supports type variables that have an upper bound or are constrained.

Customize field generation
--------------------------

The auto-generated serializer fields are configured based on type qualifiers in the dataclass (these can be mixed):

* Fields with a default value (factory) are marked as optional on the serializer (``required=False``). This means that
  these fields don't need to be supplied during deserialization.

* Fields marked as nullable through ``typing.Optional``, ``typing.Union[X, None]`` or ``X | None`` (`PEP 604`_) are
  marked as nullable on the serializer (``allow_null=True``). This means that ``None`` is accepted as a valid value
  during deserialization.

* Fields marked as final through ``typing.Final`` (as in `PEP 591`_) are marked as read-only on the serializer
  (``read_only=True``).

.. code:: Python

    @dataclass
    class Person:
        birth_date: typing.Optional[datetime.date]
        alive: bool = True
        species: typing.Final[str] = 'Human'

    # the autogenerated serializer will be equal to
    class PersonSerializer(Serializer):
        birth_date = fields.DateField(allow_null=True)
        alive = fields.BooleanField(required=False)
        species = fields.CharField(read_only=True)

Besides overriding fields by declaring them explicitly on the serializer, you can also change or override the generated
serializer field using metadata on the dataclass field. Currently, two keys are recognized in this dictionary:

* ``serializer_field`` can be used to replace the auto-generated field with a user-supplied one. Should contain an
  instance of a field, not a field type.

* ``serializer_kwargs`` can be used to specify arbitrary additional keyword arguments for the generated field. Manually
  specified arguments will have precedence over generated arguments (so e.g. by supplying ``{required: True}``, a field
  with a default value can be made required).

.. code:: Python

    @dataclasses.dataclass
    class Person:
        email: str = dataclasses.field(metadata={'serializer_field': fields.EmailField()})
        age: int = dataclasses.field(metadata={'serializer_kwargs': {'min_value': 0}})

    # the autogenerated serializer will be equal to
    class PersonSerializer(Serializer):
        email = fields.EmailField()
        age = fields.IntegerField(min_value=0)

To further customize the serializer, the ``DataclassSerializer`` accepts the following options in the ``Meta``
subclass. All options have the same behaviour as the identical options in ``ModelSerializer``.

* ``dataclass`` specifies the type of dataclass used by the serializer. This is equivalent to the ``model`` option in
  ``ModelSerializer``.

* ``fields`` and ``exclude`` can be used to specify which fields should respectively be included and excluded in the
  serializer. These cannot both be specified.

  The ``fields`` option accepts the magic value ``__all__`` to specify that all fields on the dataclass should be used.
  This is also the default value, so it is not mandatory to specify either ``fields`` or ``exclude``.

* ``read_only_fields`` can be used to mark a subset of fields as read-only.

* ``extra_kwargs`` can be used to specify arbitrary additional keyword arguments on fields. This can be useful to
  extend or change the autogenerated field without explicitly declaring the field on the serializer. This option should
  be a dictionary, mapping field names to a dictionary of keyword arguments.

  If the autogenerated field is a composite field (a list or dictionary), the arguments are applied to the composite
  field. To add keyword arguments to the composite field's child field (that is, the field used for the items in the
  list or dictionary), they should be specified as a nested dictionary under the ``child_kwargs`` name (see
  `Nested dataclasses`_ section below for an example).

  .. code:: Python

    class PersonSerializer(DataclassSerializer):
        class Meta:
            extra_kwargs = {
                'height': { 'decimal_places': 1 },
                'movie_ratings': { 'child_kwargs': { 'min_value': 0, 'max_value': 10 } }
            }

* ``validators`` functionality is unchanged.

* ``depth`` (as known from ``ModelSerializer``) is not supported, it will always nest infinitely deep.

Changing default behaviour
~~~~~~~~~~~~~~~~~~~~~~~~~~

Additionally, it is possible to change the default behaviour of the ``DataclassSerializer`` by setting one of these
properties on the class:

* The ``serializer_field_mapping`` property contains a dictionary that maps types to REST framework serializer classes.
  You can override or extend this mapping to change the serializer field classes that are used for fields based on
  their type. This dictionary also accepts dataclasses as keys to change the serializer used for a nested dataclass.

* The ``serializer_related_field`` property is the serializer field class that is used for relations to models.

* The ``serializer_union_field`` property is the serializer field class that is used for union types.

* The ``serializer_dataclass_field`` property is the serializer field class that is used for nested dataclasses. Note
  that since Python process the class body before it defines the class, this property is implemented using the
  `property decorator`_ to allow it to reference the containing class.

Finally, you can create a subclass that overrides methods of the ``DataclassSerializer``. The field generation is
controlled by the following methods, which are considered a stable part of the API:

* The ``build_unknown_field()`` method is called to create serializer fields for dataclass fields that are not
  understood. By default this just throws an error, but you can extend this with custom logic to create serializer
  fields.

* The ``build_property_field()`` method is called to create serializer fields for methods. By default this creates a
  read-only field with the method return value.

* The ``build_standard_field()``, ``build_relational_field()``, ``build_dataclass_field()``, ``build_union_field()``,
  ``build_enum_field()``, ``build_literal_field()`` and ``build_composite_field()`` methods are used to process
  respectively fields, nested models, nested dataclasses, union types, enums, literals, and lists or dictionaries. These
  can be overridden to change the field generation logic.

Note that when creating a subclass of ``DataclassSerializer``, most likely you will want to set the
``serializer_dataclass_field`` property to the subclass, so that any nested dataclasses are serialized using the
subclass as well.

.. code:: Python

    class CustomDataclassSerializer(DataclassSerializer):
        @property
        def serializer_dataclass_field(self):
            return CustomDataclassSerializer

        # Implement additional and/or override existing methods here

.. _`PEP 591`: https://www.python.org/dev/peps/pep-0591/
.. _`PEP 585`: https://www.python.org/dev/peps/pep-0585/
.. _`PEP 604`: https://www.python.org/dev/peps/pep-0604/
.. _`property decorator`: https://docs.python.org/3/library/functions.html#property

Nesting
-------

Nested dataclasses
~~~~~~~~~~~~~~~~~~

If your dataclass has a field that also contains a dataclass instance, the ``DataclassSerializer`` will automatically
create another ``DataclassSerializer`` for that field, so that its value will be nested. This also works for dataclasses
contained in lists or dictionaries, or even several layers deep.

.. code:: Python

    @dataclass
    class House:
        address: str
        owner: Person
        residents: typing.List[Person]

    class HouseSerializer(DataclassSerializer):
        class Meta:
            dataclass = House

This will serialize as:

.. code:: Python

    >>> serializer = HouseSerializer(instance=house)
    >>> serializer.data
    {
        'address': 'Main Street 5',
        'owner': { 'name': 'Alice' }
        'residents': [
            { 'name': 'Alice', 'email': 'alice@example.org', ... },
            { 'name': 'Bob', 'email': 'bob@example.org', ... },
            { 'name': 'Charles', 'email': 'charles@example.org', ... }
        ]
    }

This does not give the ability to customize the field generation of the nested dataclasses. If that is needed, you
should declare the serializer to be used for the nested field explicitly. Alternatively, you could use the
``extra_kwargs`` option to provide arguments to fields belonging to the nested dataclasses. Consider the following:

.. code:: Python

    @dataclass
    class Transaction:
       amount: Decimal
       account_number: str

    @dataclass
    class Company:
       sales: List[Transaction]

In order to tell DRF to give 2 decimal places to the transaction account number, write the serializer as follows:

.. code:: Python

    class CompanySerializer(DataclassSerializer):
        class Meta:
            dataclass = Company

            extra_kwargs = {
                'sales': {
                    # Arguments here are for the ListField generated for the sales field on Company
                    'min_length': 1,   # requires at least 1 item to be present in the sales list
                    'child_kwargs': {
                        # Arguments here are passed to the DataclassSerializer for the Transaction dataclass
                        'extra_kwargs': {
                            # Arguments here are the extra arguments for the fields in the Transaction dataclass
                            'amount': {
                                'max_digits': 6,
                                'decimal_places': 2
                            }
                        }
                    }
                }
            }

Nesting models
~~~~~~~~~~~~~~

Likewise, if your dataclass has a field that contains a Django model, the ``DataclassSerializer`` will automatically
generate a relational field for you.

.. code:: Python

    class Company(models.Model):
        name = models.CharField()

    @dataclass
    class Person:
        name: str
        employer: Company

This will serialize as:

.. code:: Python

    >>> serializer = PersonSerializer(instance=user)
    >>> print(repr(serializer))
    PersonSerializer():
        name = fields.CharField()
        employer = fields.PrimaryKeyRelatedField(queryset=Company.objects.all())
    >>> serializer.data
    {
        "name": "Alice",
        "employer": 1
    }

If you want to nest the model in the serialized representation, you should specify the model serializer to be used by
declaring the field explicitly.

If you prefer to use hyperlinks to represent relationships rather than primary keys, in the same package you can find
the ``HyperlinkedDataclassSerializer`` class: it generates a ``HyperlinkedRelatedField`` instead of a
``PrimaryKeyRelatedField``.

New serializer field types
--------------------------
To handle some types for which DRF does not ship a serializer field, some new serializer field types are shipped in the
``rest_framework_dataclasses.fields`` namespace. These fields can be used independently of the ``DataclassSerializer``
as well.

DefaultDecimalField
~~~~~~~~~~~~~~~~~~~
A subclass of `DecimalField`_ that defaults ``max_digits`` to ``None`` and ``decimal_places`` to 2. Used to represent
decimal values which there is no explicit field configured.

EnumField
~~~~~~~~~
A subclass of `ChoiceField`_ to represent Python `enumerations`_. The enumeration members can be represented by either
their name or value. The member name is used as display name.

**Signature**: ``EnumField(enum_class, by_name=False)``

* ``enum_class``: The enumeration class.
* ``by_name``: Whether members are represented by their value (``False``) or name (``True``).

IterableField
~~~~~~~~~~~~~
A subclass of `ListField`_ that can return values that aren't of type ``list``, such as ``set``.

**Signature**: ``IterableField(container=list)``

* ``container``: The type of the returned iterable. Must have a constructor that accepts a single parameter of type
  ``list``, containing the values for the iterable.

MappingField
~~~~~~~~~~~~
A subclass of `DictField`_ that can return values that aren't of type ``dict``, such as ``collections.OrderedDict``.

**Signature**: ``MappingField(container=dict)``

* ``container``: The type of the returned mapping. Must have a constructor that accepts a single parameter of type
  ``dict``, containing the values for the mapping.

UnionField
~~~~~~~~~~
A field that can serialize and deserialize values of multiple types (i.e. values of a union type). The serialized
representation of this field includes an extra discriminator field (by default named ``type``) that indicates the actual
type of the value.

.. code:: Python

    @dataclass
    class A:
        a: str

    @dataclass
    class B:
        b: int

    @dataclass
    class Response:
        obj: A | B

    class ResponseSerializer(DataclassSerializer):
        class Meta:
            dataclass = Response

.. code:: Python

    >>> response = Response(obj=A('hello'))
    >>> serializer = ResponseSerializer(instance=response)
    >>> serializer.data
    {
        'obj': {'type': 'A', 'a': 'hello'}
    }
    >>> deserializer = ResponseSerializer(data={'obj': {'type': 'B', 'b': 42}})
    >>> deserializer.is_valid()
    True
    >>> deserializer.validated_data
    Response(obj=B(b=42))

The name of the discriminator field can be changed by setting the ``discriminator_field_name`` keyword argument for the
field:

.. code:: Python

    @dataclass
    class Response:
        obj: A | B = dataclasses.field(metadata={'serializer_kwargs': {'discriminator_field_name': 'a_or_b'}})

    # or:
    class ResponseSerializer(DataclassSerializer):
        class Meta:
            dataclass = Response
            extra_kwargs = {
                'obj': {'discriminator_field_name': 'a_or_b'}
            }

Unions containing a type that does not serialize to a mapping (e.g. an integer or string) can be serialized by enabling
nesting with the ``nest_value`` keyword argument:

.. code:: Python

    @dataclass
    class Response:
        amount: int | float

    class ResponseSerializer(DataclassSerializer):
        class Meta:
            dataclass = Response
            extra_kwargs = {
                'amount': {'nest_value': True}
            }

.. code:: Python

    >>> response = Response(amount=42)
    >>> serializer = ResponseSerializer(instance=response)
    >>> serializer.data
    {
        'amount': {'type': 'int', 'value': 42}
    }

**Signature**: ``UnionField(child_fields, nest_value=False, discriminator_field_name=None, value_field_name=None)``.

* ``child_fields``: A dictionary mapping the individual types to the serializer field to be used for them.
* ``nest_value``: Whether the value should be put under a key (``True``), or merged directly into the serialized
  representation of this field (``False``). This is disabled by default, and should usually only be set to ``True`` if
  any of the union member types is a primitive.
* ``discriminator_field_name``: Name of the discriminator field, defaults to ``type``.
* ``value_field_name``: Name of the field under which values are nested if ``nest_value`` is used defaults to ``value``.

The values used in the discriminator field can be changed by subclassing ``UnionField`` and overriding the
``get_discriminator(self, type)`` method. The lone argument to this method is one of the member types of union (a key
from the ``child_fields`` parameter), and it should return the appropriate string to be used in the discriminator field
for values of this type.

.. _`enumerations`: https://docs.python.org/3/library/enum.html
.. _`ChoiceField`: https://www.django-rest-framework.org/api-guide/fields/#choicefield
.. _`DecimalField`: https://www.django-rest-framework.org/api-guide/fields/#decimalfield
.. _`ListField`: https://www.django-rest-framework.org/api-guide/fields/#listfield
.. _`DictField`: https://www.django-rest-framework.org/api-guide/fields/#dictfield

Advanced usage
--------------

* The output of methods or properties on the dataclass can be included as a (read-only) field in the serialized state
  by adding their name to the ``fields`` option in the ``Meta`` class.

* If you don't need to customize the generated fields, ``DataclassSerializer`` can also be used directly without
  creating a subclass. In that case, the dataclass should be specified using the ``dataclass`` constructor parameter:

  .. code:: Python

    serializer = DataclassSerializer(data=request.data, dataclass=Person)

* Partial updates are supported by setting the ``partial`` argument to ``True``. Nested dataclasses will also be
  partially updated, but nested fields and dictionaries will be replaced in full with the supplied value:

  .. code:: Python

    @dataclass
    class Company:
        name: str
        location: Optional[str] = None

    @dataclass
    class Person:
        name: str
        current_employer: Company
        past_employers: List[Company]

    alice = Person(name='Alice',
                   current_employer=Company('Acme Corp.', 'New York City'),
                   past_employers=[Company('PSF', 'Delaware'), Company('Ministry of Silly Walks', 'London')])

    data = {'current_employer': {'location': 'Los Angeles'}, 'past_employers': [{'name': 'OsCorp', 'location': 'NYC'}]}

    >>> serializer = PersonSerializer(partial=True, instance=alice, data=data)
    >>> print(serializer.save())
    Person(name='Alice',
           current_employer=Company('Acme Corp.', 'Los Angeles'),
           past_employers=[Company(name='OsCorp', location='NYC')])

* If you override the ``create()`` or ``update()`` methods, the dataclass instance passed in the ``validated_data``
  argument will have the special ``rest_framework.fields.empty`` value for any fields for which no data was provided.
  This is required to distinguish between not-provided fields and fields with the default value, as needed for (both
  regular and partial) updates. You can get rid of these ``empty`` markers and replace them with the default value by
  calling the parent ``update()`` or ``create()`` methods - this is the only thing they do.

  .. code:: Python

    class CompanySerializer(DataclassSerializer):
        def create(self, validated_data):
            instance = super(CompanySerializer, self).create(validated_data)
            # if no value is provided for location, these will both hold
            assert validated_data.location == rest_framework.fields.empty
            assert instance.location is None  # None is the default value of Company.location (see previous example)

  The ``validated_data`` property on the serializer has these ``empty`` markers stripped as well, and replaced with the
  default values for not-provided fields. Note that this means you cannot access ``validated_data`` on the serializer
  for partial updates where no data has been provided for fields without a default value, an Exception will be thrown.

Schemas
-------

Starting from version 0.21.2, `drf-spectacular`_ natively supports ``DataclassSerializer``. For previous versions, you
can include the `extension`_ in your project manually. You don't need to configure it, but you do need to import the
module that contains the extension.

.. _`drf-spectacular`: https://github.com/tfranzel/drf-spectacular
.. _`extension`: https://github.com/tfranzel/drf-spectacular/blob/master/drf_spectacular/contrib/rest_framework_dataclasses.py
