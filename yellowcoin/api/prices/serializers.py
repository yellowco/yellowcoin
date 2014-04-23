from rest_framework import serializers

class GetPriceSerializer(serializers.Serializer):
	bid_currency = serializers.CharField()
	ask_currency = serializers.CharField()
	price = serializers.DecimalField(max_digits=20, decimal_places=10)
	timestamp = serializers.DateTimeField()
