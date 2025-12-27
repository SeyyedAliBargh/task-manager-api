from rest_framework import serializers
from manager.models import Project

class SerializerProjects(serializers.ModelSerializer):
    absolute_url = serializers.SerializerMethodField(
        method_name="get_absolute_url"
    )
    class Meta:
        model = Project
        fields = ('id', 'owner', 'name', 'description', 'created', 'updated', 'status', 'absolute_url')
        read_only_fields = ["id", "owner", "created", "updated"]


    def get_absolute_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.pk)
    

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user.profile
        return super().create(validated_data)