from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import *
from django.db import transaction
from django.http import *
from django.shortcuts import *
from django.views.generic import *
from rest_framework import generics
from rest_framework.permissions import *
from rest_framework.response import Response
from yellowcoin.users.models import *
from yellowcoin.users.forms import *
import yellowcoin.users.signals as signals
from random import random
from django_otp_twilio_yellowcoin.models import TwilioSMSDevice
from functools import partial
from django_otp import login as otp_login
from django_otp.forms import OTPTokenForm as otp_form
from django.contrib.auth.decorators import login_required
from django_otp_twilio_yellowcoin.models import RateLimitException
from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.geoip import GeoIP
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def ResetPhone(request):
	if request.user.is_authenticated():
		return HttpResponseRedirect('/')
	pass

# consider edge cases
#	cf. http://bit.ly/1hqlSea

class ResetPassword(FormView):
	form_class = ResetPasswordForm
	template_name = 'users/reset_password.html'
	def dispatch(self, request, *args, **kwargs):
		if ('key' in kwargs):
			try:
				record = ResetRecord.objects.get(id=kwargs.get('key'), type='PW')
			except ResetRecord.DoesNotExist:
				raise Http404
			
		if request.user.is_authenticated():
			messages.error(request, 'You are already logged in!')
			return HttpResponseRedirect('/')
		return super(ResetPassword, self).dispatch(request, *args, **kwargs)

	@transaction.atomic
	def form_valid(self, form):
		try:
			user = User.objects.get(email=form.cleaned_data['email'])
			record = ResetRecord.objects.get(user=user, id=self.kwargs.get('key'), type='PW', is_valid=True)
		except ResetRecord.DoesNotExist, User.DoesNotExist:
			messages.error(self.request, 'This password link does not match the email provided.')
			return self.form_invalid(form)

		# test for time expiration
		if (timezone.now() - record.timestamp) > timedelta(hours=1):
			messages.error(self.request, 'This password link has expired.')
			record.is_valid = False
			record.save()
			return self.form_invalid(form)

		record.user.set_password(form.cleaned_data['password'])
		record.user.save()
		signals.update_password.send(sender=self.request, user=record.user)
		record.is_valid = False
		record.save()

		messages.success(self.request, 'Your password has been changed.')
		return redirect('users|login')

	def form_invalid(self, form):
		return self.render_to_response(self.get_context_data(form=form), status=400)

class ResetPasswordRequest(FormView):
	form_class = ResetPasswordRequestForm
	template_name = 'users/reset_password_request.html'

	def dispatch(self, request, *args, **kwargs):
		if request.user.is_authenticated():
			messages.error(self.request, 'You are already logged in!')
			return HttpResponseRedirect('/')
		return super(ResetPasswordRequest, self).dispatch(request, *args, **kwargs)

	@transaction.atomic
	def form_valid(self, form):
		user = User.objects.get(email__iexact=form.cleaned_data['email'], is_active=True)
		ip = self.request.META.get('HTTP_X_FORWARDED_FOR')
		if ip:
			ip = ip.split(',')[-1].strip()
		else:
			ip = self.request.META.get('REMOTE_ADDR')

		# save attempts from other IPs as documentation
		records = ResetRecord.objects.filter(user=user, ip=ip, type='PW', is_valid=True)
		if not records.exists():
			record = ResetRecord.objects.create(user=user, ip=ip, type='PW')
		else:
			record = records[0]

		messages.success(self.request, 'An email has been sent to your account.')
		signals.reset_password.send(sender=self.request, user=user, ip=ip, location=record.location, key=record.id)
		return redirect('users|reset-password')

	def form_invalid(self, form):
		messages.error(self.request, 'We couldn\'t find an account with that email address.')
		return self.render_to_response(self.get_context_data(form=form), status=400)

class RegisterUser(FormView):
	form_class = RegisterUserForm
	template_name = 'users/register.html'

	def dispatch(self, request, *args, **kwargs):
		if request.user.is_authenticated():
			messages.error(self.request, 'You are already logged in!')
			return HttpResponseRedirect('/')
		return super(RegisterUser, self).dispatch(request, *args, **kwargs)

	@transaction.atomic
	def form_valid(self, form):
		if (settings.MAX_USERS >= 0) and (User.objects.count() >= settings.MAX_USERS - 1):
			messages.error(self.request, 'Registration is currently closed.')
			return self.form_invalid(form)
		user_object = User.objects.create_user(form.cleaned_data['email'], form.cleaned_data['password'])
		if 'referrer' in self.request.session:
			user_object.referrer = User.objects.get(id=self.request.session['referrer'])
		user_object.save()
		signals.create_account.send(sender=self.request, user=user_object)
		messages.success(self.request, 'Success! An activation email has been sent to the address provided.')
		return redirect('users|login')

	def form_invalid(self, form):
		messages.error(self.request, 'Some errors occurred when we tried to make your account.')
		return self.render_to_response(self.get_context_data(form=form), status=400)

class ActivateUser(FormView):
	form_class = ActivateUserForm
	template_name = 'users/activate.html'

	def dispatch(self, request, *args, **kwargs):
		if self.request.user.is_authenticated():
			messages.error(self.request, 'You are already logged in!')
			return HttpResponseRedirect('/')
		return super(ActivateUser, self).dispatch(request, *args, **kwargs)

	def form_valid(self, form):
		messages.success(self.request, 'Account activated! You may now log in.')
		return redirect('users|login')

	def form_invalid(self, form):
		messages.error(self.request, 'Nope, couldn\'t activate that user account, sorry!')
		return self.render_to_response(self.get_context_data(form=form), status=400)

def activate(request, code):
	try:
		activator = EmailValidation.objects.get(key=code)
		activator.delete()
		messages.success(request, 'Email verified!')
		return redirect('users|login')
	except:
		messages.error(request, 'Nope, couldn\'t activate that user account, sorry!')
		return redirect('users|activate-manual')

class ValidateEmailUpdate(View):
	def get(self, request, *args, **kwargs):
		ev = get_object_or_404(EmailValidation, key=kwargs['key'])
		ev.user.email = ev.email
		ev.user.save()
		ev.delete()
		return redirect('users|login')

def Referral(request, referral_id=None):
	if not request.user.is_authenticated() and referral_id is not None:
		user = User.objects.from_referral_id(referral_id)
		if user is not None:
			request.session['referrer'] = user.id
	return HttpResponseRedirect('/')

# log into the website
def Login(request):
	if request.user.is_authenticated():
		return HttpResponseRedirect('/')
	elif 'username' in request.POST and 'password' in request.POST:
		email = request.POST.get('username')
		password = request.POST.get('password')
		ip = request.META.get('HTTP_X_FORWARDED_FOR')
		if ip:
			ip = ip.split(',')[-1].strip()
		else:
			ip = request.META.get('REMOTE_ADDR')
		user = authenticate(username=email, password=password)
		if user is not None:
			login(request, user)
			if user.use_2fa and user.profile.valid_phone:
				return redirect('users|verify')
			elif not user.is_superuser:
				login_record = LoginRecord.objects.create(user=user, ip=ip, is_successful=True)
				signals.login.send(sender=request, user=user, ip=ip, location=login_record.location)
				messages.success(request, 'You have been logged in!')
				return redirect('application')
			elif user.is_superuser:
				# TODO -- fix this
				return redirect('/admin/')
		else:
			try:
				user = User.objects.get(email=email)
				login_record = LoginRecord.objects.create(user=user, ip=ip, is_successful=False)
				signals.login_failed.send(sender=request, user=user, ip=ip, location=login_record.location)
			except User.DoesNotExist:
				pass # email wrong
			messages.error(request, 'Wrong username and password combination.')
	return render(request, 'users/login.html', status=400)

# logout of the website
def Logout(request):
	logout(request)
	return redirect('/')

# two factor authentication
def Verify(request):
	# if not logged in
	if isinstance(request.user, AnonymousUser):
		return redirect('users|login')
	if request.user.is_verified():
		# The user is either logged in or does not have 2fa enabled
		return redirect('application')
	if request.user.is_authenticated() and (request.user.profile.valid_phone or request.user.profile.payment_network.billing_address.phone is None):
		# The user is logged in and is not attempting to verify their phone
		return redirect('application')
		
	# send the OTP - only for a GET request
	if 'otp_token' not in request.POST:
		try:
			TwilioSMSDevice.objects.get(user=request.user.id).generate_challenge()
		except TwilioSMSDevice.DoesNotExist:
			# this should never happen
			messages.error(request, 'You do not have a phone set up for two-factor authentication - please contact customer support')
			return HttpResponseRedirect('/')
		except RateLimitException:
			messages.error(request, 'You are asking for the OTP too quickly - please wait for a bit')
		except Exception as e:
			messages.error(request, 'Twilio Exception - %s' % str(e))
	# tests OTP
	else:
		phone_object = TwilioSMSDevice.objects.get(user=request.user)

		ip = request.META.get('HTTP_X_FORWARDED_FOR')
		if ip:
			ip = ip.split(',')[-1].strip()
		else:
			ip = request.META.get('REMOTE_ADDR')

		# sets user.is_verified()
		if phone_object.verify_token(request.POST['otp_token']):
			if request.user.profile.valid_phone:
				# they are attempting to log in
				#	cf http://bit.ly/1l3FEgS
				otp_login(request, phone_object)
				login_record = LoginRecord.objects.create(user=request.user, ip=ip, is_successful=True)
				signals.login.send(sender=request, user=request.user, ip=ip, location=login_record.location)
				messages.success(request, 'You have been logged in!')
			else:
				# they are attempting to verify their phone number
				request.user.profile.valid_phone = True
				request.user.profile.save()
				messages.success(request, 'Your phone number has been verified')
			return redirect('application')
		else:
			if request.user.profile.valid_phone:
				login_record = LoginRecord.objects.create(user=request.user, ip=ip, is_successful=False)
				signals.login.send(sender=request, user=request.user, ip=ip, location=login_record.location)
			messages.error(request, 'Incorrect OTP, please try again')

	return render(request, 'users/verify.html', status=400)
