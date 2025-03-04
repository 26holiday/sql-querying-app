from rest_framework import serializers

class QuerySerializer(serializers.Serializer):
    query = serializers.CharField(help_text="The SQL query to be processed.")
