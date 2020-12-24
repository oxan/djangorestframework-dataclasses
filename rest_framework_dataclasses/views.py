import dataclasses
import functools
import inspect
import typing
from collections import namedtuple
from typing import Iterable, Tuple, Any, Dict, Callable

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings

from rest_framework_dataclasses import field_utils
from rest_framework_dataclasses.settings import dataclass_serializer_settings


_FieldDefinition = namedtuple('_FieldDefinition', ('name', 'hint', 'type_info', 'has_default', 'default', 'serializer'))


def _make_dataclass_serializer(dataclass: type, serializer_fields: Dict[str, Any] = None):
    if not serializer_fields:
        serializer_fields = {}
    serializer_fields['Meta'] = type('Meta', (), {'dataclass': dataclass})
    serializer_parents = (dataclass_serializer_settings.DEFAULT_DATACLASS_SERIALIZER, )
    serializer_type = type(f'{dataclass.__name__}Serializer', serializer_parents, serializer_fields)
    return serializer_type


def _make_serializer(name: str, fields: Iterable[_FieldDefinition]):
    dataclass_fields = []
    serializer_fields = {}
    for field in fields:
        default = field.default if field.has_default else dataclasses.MISSING
        dataclass_fields.append((field.name, field.hint, dataclasses.field(default=default)))
        if field.serializer is not None:
            serializer_fields[field.name] = field.serializer(many=field.type_info.is_many)

    dataclass = dataclasses.make_dataclass(name, dataclass_fields)
    return dataclass, _make_dataclass_serializer(dataclass, serializer_fields)


def typed_view(view_function: Callable = None, *, body: str = '', serializers: Dict[str, type] = None):
    # Accept both @typed_view and @typed_view(...) invocations
    if not view_function:
        return functools.partial(typed_view, body=body, serializers=serializers)

    if not serializers:
        serializers = {}

    # We can't directly use the annotations returned by inspect.signature, as those don't have resolved references.
    signature = inspect.signature(view_function)
    signature_hints = typing.get_type_hints(view_function)
    inject_parameters = {param.name: (signature_hints.get(param.name, None), param.default)
                         for param in signature.parameters.values()}
    is_method = bool(inject_parameters.pop('self', None))

    # If it isn't explicitly specified for which parameter the request body should be used, use it for the first
    # dataclass parameter, if there is any.
    if body == '':
        body = next((name for name, (hint, _) in inject_parameters.items() if dataclasses.is_dataclass(hint)), None)
    elif body not in inject_parameters:
        raise Exception(f'The specified body parameter {body} on typed view {view_function.__qualname__} does not '
                        f'exist.')

    # Make sure we can inject something for every non-optional parameter.
    for name, (hint, default) in inject_parameters.items():
        if hint is None and default is inspect.Parameter.empty:
            raise Exception(f'Typed view {view_function.__qualname__} parameter {name} must have type annotation or '
                            f'default value.')

    # Determine where we (optionally) have to inject the request.
    request_parameter = next((key for key, (hint, default) in inject_parameters.items() if hint is Request), None)
    inject_parameters.pop(request_parameter, None)

    # Determine serializer for the request, if there is something to inject.
    request_serializer_type = None
    if len(inject_parameters) > 0:
        if len(inject_parameters) == 1 and body is not None and dataclasses.is_dataclass(inject_parameters[body][0]):
            # Optimization: in the common case where the body is the single parameter to be injected, don't wrap it
            # inside another dataclass for serialization.
            request_dataclass = inject_parameters[body][0]
            request_serializer_type = serializers.get(body, _make_dataclass_serializer(request_dataclass))
            request_optimized = True
        else:
            # Generic case: when more than just the body is injected, construct a dataclass type to deserialize all
            # parameters into.
            request_fields = {name: _FieldDefinition(name, hint, field_utils.get_type_info(hint),
                                                     default != inspect.Parameter.empty, default,
                                                     serializers.get(name, None))
                              for name, (hint, default) in inject_parameters.items()}
            request_dataclass, request_serializer_type = _make_serializer('Request', request_fields.values())
            request_optimized = False

    # Determine serializer for the response.
    response_serializer_type = None
    if 'return' not in signature_hints:
        raise Exception(f'Typed view {view_function.__qualname__} must have a return type annotation.')
    elif signature_hints['return'] is not Response:
        if dataclasses.is_dataclass(signature_hints['return']):
            # Optimization: if a dataclass is returned, we can serialize that directly.
            response_dataclass = signature_hints['return']
            response_serializer_type = serializers.get('return', _make_dataclass_serializer(response_dataclass))
            response_optimized = True
        else:
            # Generic case: construct a dataclass type to serialize the result from.
            response_fields = [_FieldDefinition('response', signature_hints['return'],
                                                field_utils.get_type_info(signature_hints['return']),
                                                False, None, serializers.get('return', None))]
            response_dataclass, response_serializer_type = _make_serializer('Response', response_fields)
            response_optimized = False

    # The actual wrapper of the view function
    @functools.wraps(view_function)
    def view_wrapper(*args, **kwargs):
        args = list(args)
        view_args = (args.pop(False), ) if is_method else ()
        view_kwargs = {}

        # Try to detect if we're invoked as a view, and just passthrough if we're not -- this heuristic isn't perfect.
        if len(args) != 1 or not isinstance(args[0], Request):
            return view_function(*view_args, *args, **kwargs)

        request = args.pop()
        serializer_context = {'request': request, 'format': kwargs.get(api_settings.FORMAT_SUFFIX_KWARG, None)}
        if is_method:
            serializer_context['view'] = view_args[0]

        if request_parameter is not None:
            view_kwargs[request_parameter] = request

        if request_serializer_type is not None:
            if request_optimized:
                request_serializer = request_serializer_type(data=request.data, context=serializer_context)
                request_serializer.is_valid(raise_exception=True)
                view_kwargs[body] = request_serializer.save()
            else:
                # Get rid of query parameters being multiple valued when not requested.
                request_data = {k: v if request_fields[k].type_info.is_many else v[-1]
                                for k, v in request.query_params.lists() if k in request_fields}
                if body is not None:
                    request_data[body] = request.data

                request_serializer = request_serializer_type(data=request_data, context=serializer_context)
                request_serializer.is_valid(raise_exception=True)
                view_kwargs.update(dataclasses.asdict(request_serializer.save()))

        view_return = view_function(*view_args, **view_kwargs)

        if response_serializer_type is not None:
            if response_optimized:
                response_serializer = response_serializer_type(instance=view_return, context=serializer_context)
                return Response(response_serializer.data)
            else:
                response_data = response_dataclass(view_return)
                response_serializer = response_serializer_type(instance=response_data, context=serializer_context)
                return Response(response_serializer.data['response'])

        return view_return

    return view_wrapper
