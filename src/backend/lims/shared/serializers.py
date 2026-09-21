from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from coreadmin.utils.serializers import CustomModelSerializer


class StrictRow(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    sequence = serializers.IntegerField(min_value=0, max_value=2147483647)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise ValidationError('Unknown composition fields.')
        return super().to_internal_value(data)


class MasterSerializer(CustomModelSerializer):
    row_model = None

    def validate(self, attrs):
        if self.instance and 'number' in attrs and attrs['number'] != self.instance.number:
            raise ValidationError({'number': 'Number cannot change after creation.'})
        return attrs
