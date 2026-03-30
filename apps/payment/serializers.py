from rest_framework import serializers

class FlutterWaveHookSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    data = serializers.JSONField() #.data is a serializer's inbuilt prop. hence, always access .validated_data
    timestamp = serializers.DateTimeField()
    type = serializers.CharField()
