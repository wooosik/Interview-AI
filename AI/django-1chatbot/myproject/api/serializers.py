from api.models import chat 
from rest_framework import serializers

class ChatSerializer(serializers.ModelSerializer):
    # class Meta:
    #     model = chat
    #     fields = '__all__'
    prompt = serializers.CharField()
    response = serializers.CharField()