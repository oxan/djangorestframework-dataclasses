import dataclasses
import functools
import inspect

from rest_framework.response import Response
from rest_framework.settings import api_settings

from rest_framework_dataclasses.serializers import DataclassSerializer


def typed_view(view_function=None, *, body='', serializers=None):
    # Accept both @typed_view and @typed_view(...) invocations
    if not view_function:
        return functools.partial(typed_view, body=body, serializers=serializers)

    primitive_types = (bool, float, int, str)
    if not serializers:
        serializers = {}

    signature = inspect.signature(view_function)
    inject_parameters = signature.parameters.copy()
    is_method = bool(inject_parameters.pop('self', None))

    # Make sure we can inject the type of every non-optional parameter.
    for param in inject_parameters.values():
        if param.annotation == inspect.Parameter.empty and param.default == inspect.Parameter.empty:
            raise Exception(f'Typed view {view_function.__qualname__} parameter {param.name} must have type annotation '
                            f'or default value.')

        if param.annotation not in primitive_types and not dataclasses.is_dataclass(param.annotation):
            raise Exception(f'Typed view {view_function.__qualname__} parameter {param.name} must be of a primitive or '
                            f'dataclass type, or have a default value.')

    # If it isn't explicitly specified for which parameter the request body should be used, use it for the first
    # non-primitive parameter, if there is any.
    if body == '':
        body = next((p.name for p in inject_parameters.values() if p.annotation not in (bool, float, int, str)), None)
    elif body not in inject_parameters:
        raise Exception(f'The specified body parameter {body} on typed view {view_function.__qualname__} cannot be '
                        f'injected.')

    # Determine serializer for the request, if there is something to inject.
    request_serializer_type = None
    if len(inject_parameters) > 0:
        if(len(inject_parameters) == 1 and body is not None and
                dataclasses.is_dataclass(inject_parameters[body].annotation)):
            # Optimization: in the common case where the body is the single parameter to be injected, don't wrap it
            # inside another dataclass for serialization.
            request_dataclass = inject_parameters[body].annotation
            request_optimized = True
        else:
            # Generic case: when more than just the body is injected, construct a dataclass type to deserialize all
            # parameters into.
            request_fields = []
            for param in inject_parameters.values():
                field_default = param.default if param.default != inspect.Parameter.empty else dataclasses.MISSING
                request_fields.append((param.name, param.annotation, dataclasses.field(default=field_default)))

            request_dataclass = dataclasses.make_dataclass('RequestData', request_fields)
            request_optimized = False

        request_serializer_type = serializers.get(request_dataclass,
                                                  functools.partial(DataclassSerializer, dataclass=request_dataclass))

    # Determine serializer for the response.
    response_serializer_type = None
    if signature.return_annotation is inspect.Signature.empty:
        raise Exception(f'Typed view {view_function.__qualname__} must have a return type annotation.')
    elif signature.return_annotation is not Response:
        if dataclasses.is_dataclass(signature.return_annotation):
            # Optimization: if a dataclass is returned, we can serialize that directly.
            response_dataclass = signature.return_annotation
            response_optimized = True
        else:
            # Generic case: construct a dataclass type to serialize the result from.
            response_dataclass = dataclasses.make_dataclass('ResponseData', [('response', signature.return_annotation)])
            response_optimized = False

        response_serializer_type = serializers.get(response_dataclass,
                                                   functools.partial(DataclassSerializer, dataclass=response_dataclass))

    @functools.wraps(view_function)
    def view_wrapper(*args, **kwargs):
        args = list(args)
        view_args = (args.pop(False), ) if is_method else ()
        view_kwargs = {}

        request = args.pop()
        serializer_context = {'request': request, 'format': kwargs.get(api_settings.FORMAT_SUFFIX_KWARG, None)}
        if is_method:
            serializer_context['view'] = view_args[0]

        if request_serializer_type is not None and request_optimized:
            request_serializer = request_serializer_type(data=request.data, context=serializer_context)
            request_serializer.is_valid(raise_exception=True)
            view_kwargs[body] = request_serializer.save()
        elif request_serializer_type is not None:
            # Compromise here: when a key is supplied once we use just that value, otherwise we treat it as a list.
            # Note that this makes it impossible to supply a list with just one item for now.
            request_data = {k: v[0] if len(v) == 1 else v for k, v in request.query_params.lists()}
            if body is not None:
                request_data[body] = request.data

            request_serializer = request_serializer_type(data=request_data, context=serializer_context)
            request_serializer.is_valid(raise_exception=True)
            view_kwargs.update(dataclasses.asdict(request_serializer.save()))

        view_return = view_function(*view_args, **view_kwargs)

        if response_serializer_type is not None and response_optimized:
            response_serializer = response_serializer_type(instance=view_return, context=serializer_context)
            return Response(response_serializer.data)
        elif response_serializer_type is not None:
            response_data = response_dataclass(view_return)
            response_serializer = response_serializer_type(instance=response_data, context=serializer_context)
            return Response(response_serializer.data)
        else:
            return view_return

    return view_wrapper
