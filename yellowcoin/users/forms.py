from django import forms
from django.contrib.auth.forms import AuthenticationForm 
from yellowcoin.users.models import User, EmailValidation
from django_otp.forms import OTPTokenForm

class RegisterUserForm(forms.Form):
	email = forms.EmailField()
	password = forms.CharField()
	password_confirm = forms.CharField()
	tos = forms.BooleanField(required=True)

	def clean_email(self):
		email = self.cleaned_data['email']
		if User.objects.filter(email__iexact=email).exists():
			raise forms.ValidationError('This email is already registered.')
		return email

	def clean(self):
		cleaned_data = super(RegisterUserForm, self).clean()
		password = cleaned_data.get('password')
		password_confirm = cleaned_data.get('password_confirm')
		if (password and password_confirm) and (password != password_confirm):
			self._errors['password_confirm'] = self.error_class(['Passwords do not match.'])
			del cleaned_data['password']
			del cleaned_data['password_confirm']
		return cleaned_data

class ActivateUserForm(forms.Form):
	email = forms.EmailField()
	key = forms.CharField()
	
	def clean_key(self):
		key = self.cleaned_data['key']
		try:
			activation = EmailValidation.objects.get(key=key)
			self.request.user.is_active = True
			self.request.user.save()
			activation.delete()
		except:
			raise forms.ValidationError('Invalid activation key.')
		return key

class EmailLoginForm(AuthenticationForm):
	def __init__(self, *args, **kwargs):
		super(EmailLoginForm, self).__init__(*args, **kwargs)
		self.error_messages['inactive'] = 'This account is inactive or has been disabled.'

	def clean_username(self):
		email = self.cleaned_data['username']
		return email

# cf http://bit.ly/1dtuDCJ
class VerifyForm(OTPTokenForm):
	otp_token = forms.CharField()

	def clean_otp_token(self):
		otp_token = str(self.cleaned_data['otp_token'])
		return otp_token
