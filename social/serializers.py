from rest_framework import serializers
from .models import Notification, Report, Complaint
from django.contrib.auth import get_user_model
from accounts.models import Agent

User = get_user_model()

class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar']

class NotificationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class NotificationSerializer(serializers.ModelSerializer):
    actor = NotificationUserSerializer(read_only=True)
    research_node = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'notification_type', 'actor', 'research_node', 'verb', 'created_at', 'is_read']

    def get_research_node(self, obj):
        if obj.research_node:
            return {'id': obj.research_node.id, 'title': obj.research_node.title}
        return None

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['reason', 'description']

class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ['category', 'description', 'reference_id']
