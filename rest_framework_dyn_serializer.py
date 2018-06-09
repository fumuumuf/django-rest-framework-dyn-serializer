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
                self.request_all_allowed_fields()
        else:
            self.request_all_allowed_fields()

    def get_request(self):
        return self.context.get('request')

    def exclude_omitted_fields(self, request, parent_limit_fields=False):
        """
        exclude omitted fields if parent_limit_fields or limit_fields are True.
        if both are False, all fields are appear.
        """

        limit_fields = getattr(self, 'limit_fields', parent_limit_fields)
        field_names = self.get_requested_field_names(request)
        self._requested_fields = field_names

        if limit_fields and field_names is not None:
            # Drop any fields that are not specified in passed query param
            allowed = set(field_names)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        for field_name in self.fields:
            field = self.fields[field_name]

            if isinstance(field, serializers.ListSerializer):
                if isinstance(field.child, DynSerializerMixin):
                    field.child.exclude_omitted_fields(request, limit_fields)
            elif isinstance(field, DynSerializerMixin):
                field.exclude_omitted_fields(request, limit_fields)

    def request_all_allowed_fields(self):
        pass

    def get_requested_field_names(self, request):
        return set(self.fields.keys())


class DynModelSerializer(DynSerializerMixin, serializers.ModelSerializer):
    """
    Factory to include/exclude fields dynamically
    """
    default_error_messages = {
        'does_not_exist': 'Invalid pk "{pk_value}" - object does not exist.',
        'incorrect_type': 'Incorrect type. Expected pk value, received {data_type}.',
    }

    def __init__(self, *args, **kwargs):
        self._requested_fields = []

        s_type = type(self)
        assert hasattr(self.Meta, 'model'), '{} Meta.model param is required'.format(s_type)
        assert hasattr(self.Meta, 'fields_param'), \
            '{} Meta.fields_param param cannot be empty'.format(s_type)

        self.nested = kwargs.pop('nested', False)
        self.default_fields = list(getattr(self.Meta, 'default_fields', ['id']))
        self.limit_fields = kwargs.pop('limit_fields', getattr(self.Meta, 'limit_fields', False))

        self.set_allowed_fields(kwargs.pop('fields', None))

        for field_name in self.default_fields:
            assert field_name in self._allowed_fields, '{} Meta.default_fields contains field "{}"'\
                                                       'not in Meta.fields list'.format(s_type,
                                                                                        field_name)

        super(DynModelSerializer, self).__init__(*args, **kwargs)

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

    def request_all_allowed_fields(self):
        for field in self._allowed_fields:
            self._requested_fields.append(field)

    def set_allowed_fields(self, fields=None):
        if hasattr(self.Meta, 'fields'):
            meta_fields = list(self.Meta.fields)
        else:
            meta_fields = []
            for field_obj in self.Meta.model._meta.get_fields():
                meta_fields.append(field_obj.name)

        include = meta_fields if not fields else [
            field for field in meta_fields if field in fields]
        exclude = set(getattr(self.Meta, 'exclude', []))

        self._allowed_fields = list(set(include) - exclude)

    def get_requested_field_names(self, request):
        fields_param_value = request.query_params.get(self.Meta.fields_param)
        if fields_param_value is not None:
            requested_fields = fields_param_value.split(',')
            if requested_fields:
                return list(set(self._allowed_fields).intersection(set(requested_fields)))
        return list(self.default_fields)

    def is_field_requested(self, field_name):
        """
        Return True if the field requested by client
        """
        if self.limit_fields:
            request = self.get_request()
            assert request, "request can't be None in limit_fields mode"
            requested_fields = self.get_requested_field_names(request)
            return field_name in requested_fields
        else:
            # always return field if limit_fields flag set to False
            return True

    def get_field_names(self, declared_fields, info):
        """
        Return only requested and allowed field names
        """
        return self._requested_fields

    class Meta:
        model = None
        fields = []
        default_fields = []
        fields_param = None
