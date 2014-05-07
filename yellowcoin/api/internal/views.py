from django.db import transaction
from django.conf import settings
from django.shortcuts import *
from django.utils import timezone
from django.views.generic import *
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework.authentication import SessionAuthentication
from rest_framework import generics, serializers
from rest_framework.permissions import *
from rest_framework.response import Response
from django_routing_numbers import Institution
from yellowcoin.users.models import User, WaitlistRecord
from yellowcoin.users import signals
import requests

class LookupBankRoutingNumber(generics.RetrieveAPIView):
	authentication_classes = (SessionAuthentication,)
	permission_classes = ( IsAuthenticated, )
	serializer_class = serializers.Serializer
	def get(self, request, routing_number):
		try:
			name = Institution.objects.get(routing_number=routing_number).customer_name
		except Institution.DoesNotExist:
			name = 'Unknown'
		return Response({'name':name}, status=200)

class ResendValidationEmail(generics.CreateAPIView):
	authentication_classes = (SessionAuthentication,)
	permission_classes = (IsAuthenticated,)
	serializer_class = serializers.Serializer
	def post(self, request):
		if request.user.activation_key:
			signals.create_account.send(sender=request, user=request.user)
			return Response("", status=200)
		else:
			return Response("", status=400)

class AddWaitlistEmail(generics.CreateAPIView):
	permission_classes = (AllowAny,)
	serializer_class = serializers.Serializer
	def post(self, request):
		try:
			validate_email(request.DATA.get('email', ''))
		except ValidationError as e:
			return Response("Your email was invalid", status=400)
		except:
			return Response("Something went wrong...", status=500)
		if (settings.MAX_USERS >= 0) and (User.objects.count() >= settings.MAX_USERS):
			try:
				User.objects.get(email=request.DATA['email'])
				return Response("That email address already has an account", status=400)
			except:
				pass
			try:
				WaitlistRecord.objects.get(content=request.DATA['email'])
				return Response("That email address is already waitlisted", status=400)
			except:
				pass
			ip = request.META.get('HTTP_X_FORWARDED_FOR')
			if ip:
				ip = ip.split(',')[-1].strip()
			else:
				ip = request.META.get('REMOTE_ADDR')
			WaitlistRecord.objects.create(ip=ip, content=request.DATA['email']).save()
			return Response("", status=200)
		else:
			return Response("The waitlist is closed", status=403)

