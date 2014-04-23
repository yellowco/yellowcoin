from rest_framework.permissions import BasePermission

# cf. http://bit.ly/1dQVzAE

SAFE_METHODS = [ 'GET', 'HEAD', 'OPTIONS' ]

class IsAuthenticatedOrReadOnly(BasePermission):
	def has_permission(self, request, view):
		if (request.method in SAFE_METHODS) or (request.user and request.user.is_authenticated()):
			return True
		return False
