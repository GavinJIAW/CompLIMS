from django.db import transaction


class MessageService:
    @staticmethod
    def create(serializer, **attribution):
        with transaction.atomic():
            return serializer.save(**attribution)

    @staticmethod
    def read(view):
        from coreadmin.system.models import MessageCenterTargetUser
        from coreadmin.utils.json_response import DetailResponse
        with transaction.atomic():
            instance = view.get_object()  # B2 scope/object before any side effect.
            relation = MessageCenterTargetUser.objects.select_for_update().filter(
                users=view.request.user, messagecenter=instance).first()
            if relation is not None:
                relation.is_read = True
                relation.save(update_fields=['is_read'])
            data = view.get_serializer(instance).data
            return DetailResponse(data=data, msg='Success')
