from yellowcoin.users.models import User
from rest_framework import authentication
from rest_framework import exceptions

class APIKeyAuthentication(authentication.BaseAuthentication):
	def authenticate(self, request):
		api_key = request.META.get('HTTP_X_API_KEY', request.GET.get('api_key'))
		if api_key:
			try:
				user = User.objects.get(profile__api_key=api_key)
			except:
				raise exceptions.AuthenticationFailed('Invalid API key')
			return (user, None)
		else:
			return None
