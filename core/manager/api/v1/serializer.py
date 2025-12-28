from rest_framework import serializers
from manager.models import Project

class SerializerProjects(serializers.ModelSerializer):
    absolute_url = serializers.SerializerMethodField(
        method_name="get_absolute_url"
    )
    role = serializers.SerializerMethodField(
        method_name="get_role"
    )
    class Meta:
        model = Project
        fields = ('id', 'owner', 'name', 'role', 'description', 'created', 'updated', 'status', 'absolute_url')
        read_only_fields = ["id", "owner", "created", "updated"]


        def get_role(self, obj):
            profile = self.context['request'].user.profile

            # اگر صاحب پروژه است
            if obj.owner_id == profile.id:
                return 'owner'

            # اگر عضو است
            membership = getattr(obj, 'current_user_membership', None)
            if membership:
                return membership[0].role

            return None

    def get_absolute_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.pk)
    

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user.profile
        return super().create(validated_data)