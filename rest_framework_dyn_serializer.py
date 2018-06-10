from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers


class DynSerializerMixin:
    """
    A serializer non inherited DynModelSerializer must inherit this mixin if it have DynModelSerializer Fields.
    """

    def __init__(self, *args, **kwargs):
        super(DynSerializerMixin, self).__init__(*args, **kwargs)

        request = self.get_request()

        if request:
            # don't limit fields for write operations
            if request.method == 'GET':
                self.exclude_omitted_fields(request)

                for field_name, field_name in self.fields.items():
                    # assigning parent context to allow child serializers to update their fields
                    # later
                    field_name._context = self.context
            else:
                self.limit_fields = False

    def get_request(self):
        return self.context.get('request')

    def exclude_omitted_fields(self, request, parent_limit_fields=False):
        """
        exclude omitted fields if parent_limit_fields or limit_fields are True.
        if both are False, all fields are appear.
        """

        self.limit_allowed_fields()

        is_limit_fields = getattr(self, 'limit_fields', None)
        if is_limit_fields is None:
            is_limit_fields = parent_limit_fields

        if is_limit_fields:
            self._exclude_omitted_fields(request)

        for field_name in self.fields:
            field = self.fields[field_name]

            if isinstance(field, serializers.ListSerializer):
                if isinstance(field.child, DynSerializerMixin):
                    field.child.exclude_omitted_fields(request, is_limit_fields)
            elif isinstance(field, DynSerializerMixin):
                field.exclude_omitted_fields(request, is_limit_fields)

    def limit_allowed_fields(self):
        pass

    def _exclude_omitted_fields(self, request):
        pass


class DynModelSerializer(DynSerializerMixin, serializers.ModelSerializer):
    """
    Factory to include/exclude fields dynamically
    """
    default_error_messages = {
        'does_not_exist': 'Invalid pk "{pk_value}" - object does not exist.',
        'incorrect_type': 'Incorrect type. Expected pk value, received {data_type}.',
    }

    def __init__(self, *args, **kwargs):

        s_type = type(self)
        assert hasattr(self.Meta, 'model'), '{} Meta.model param is required'.format(s_type)
        assert hasattr(self.Meta, 'fields_param'), \
            '{} Meta.fields_param param cannot be empty'.format(s_type)

        self.nested = kwargs.pop('nested', False)
        self.default_fields = list(getattr(self.Meta, 'default_fields', ['id']))
        self.limit_fields = kwargs.pop('limit_fields', getattr(self.Meta, 'limit_fields', None))
        self._allowed_fields_by_param = kwargs.pop('fields', None)

        super(DynModelSerializer, self).__init__(*args, **kwargs)

        for field_name in self.default_fields:
            assert field_name in self.allowed_fields, '{} Meta.default_fields contains field "{}"' \
                                                      'not in Meta.fields list'.format(s_type,
                                                                                       field_name)

    def get_value(self, data):
        if not self.nested or self.field_name not in data:
            return super().get_value(data)
        return data[self.field_name]

    def to_internal_value(self, data):
        """
        Allow pass value of nested field, assume that passed value is PK
        """
        if not self.nested:
            return super().to_internal_value(data)
        try:
            return self.Meta.model.objects.get(pk=data)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', pk_value=data)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data).__name__)

    def get_requested_field_names(self, request):
        fields_param_value = request.query_params.get(self.Meta.fields_param)

        if fields_param_value is None:
            return list(self.default_fields)

        param_values = set(fields_param_value.split(','))
        return list(param_values)

    def is_field_requested(self, field_name):
        """
        Return True if the field requested by client
        """
        if self.limit_fields:
            request = self.get_request()
            assert request, "request can't be None in limit_fields mode"
            requested_fields = self.get_requested_field_names(request)
            return field_name in requested_fields and field_name in self.allowed_fields
        else:
            # always return field if limit_fields flag set to False
            return True

    @property
    def allowed_fields(self):
        if not hasattr(self, '_allowed_fields'):
            self.limit_allowed_fields()
        return self._allowed_fields

    def limit_allowed_fields(self):
        """
        limit fields by a init's argument:`fields`.

        this method is called before call _exclude_omitted_fields.
        (exclude omitted fields from limited fields by this function.)
        """
        if self._allowed_fields_by_param:
            exclude_fields = [n for n in self.fields.keys() if n not in self._allowed_fields_by_param]
            for name in exclude_fields:
                self.fields.pop(name)

        self._allowed_fields = [n for n in self.fields.keys()]

    def _exclude_omitted_fields(self, request):

        enabled_fields = self.get_requested_field_names(request)

        allowed = set(enabled_fields)
        existing = set(self.fields.keys())
        for field_name in existing - allowed:
            self.fields.pop(field_name)

    class Meta:
        model = None
        fields = []
        default_fields = []
        fields_param = None
