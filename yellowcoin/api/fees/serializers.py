from rest_framework import serializers

class GetFeeSerializer(serializers.Serializer):
	bid_currency = serializers.CharField()
	ask_currency = serializers.CharField()
	bid_val = serializers.DecimalField()
	bid_fee = serializers.DecimalField()
	ask_val = serializers.DecimalField()
	ask_fee = serializers.DecimalField()
