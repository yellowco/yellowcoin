from django.conf import settings
from django.core.mail import send_mail
from django.dispatch import Signal, receiver
from django.http import HttpRequest
from django.template import Context
from django.template.loader import render_to_string
from template_email import TemplateEmail

def create_email_signal(providing_args, subject, key, template=None):
	signal = Signal(providing_args=['user'] + providing_args)
	def render(sender, **kwargs):
		def is_notification_enabled(user, medium, key):
			notifications = user.retrieve('notifications', None)
			if notifications and medium in notifications and key in notifications[medium] and not notifications[medium][key]:
				return False
			return True
		user = kwargs.get('user', None)
		if user:
			if is_notification_enabled(user, 'email', key):
				return TemplateEmail(
					template=template,
					to=[kwargs.get('email', user.email)],
					context=kwargs
				).send()
			if is_notification_enabled(user, 'sms', key):
				# TODO: Send SMS
				pass
	signal.connect(render, weak=False)
	return signal

login = create_email_signal(['ip', 'location'], 'Successful Authorization', 'login', 'users/email/login.html')
create_account = create_email_signal([], 'Account Activation', 'create_account', 'users/email/create_account.html')
start_transaction = Signal(providing_args=['user', 'transaction'])
end_transaction = Signal(providing_args=['user', 'transaction'])
action_required = create_email_signal(['message'], 'Action Required', 'action_required', 'users/email/action_required.html')
update_profile = create_email_signal([], 'Profile Updated', 'update_profile', 'users/email/update_profile.html')
update_password = create_email_signal([], 'Password Changed', 'update_password', 'users/email/update_password.html')
create_bank_account = create_email_signal(['bank_account'], 'Bank Account Added', 'create_bank_account', 'users/email/create_bank_account.html')
create_crypto_account = create_email_signal(['crypto_account'], 'Crypto Account Added', 'create_crypto_account', 'users/email/create_crypto_account.html')
referral_completed = create_email_signal(['address', 'email', 'txid'], 'Referral Completd', 'referral_completed', 'users/email/referral_completed.html')

def check_referral(sender, **kwargs):
	user = kwargs.get('user', None)
	if user and user.referrer and not user.is_referrer_paid:
		try:
			referral_account = user.referrer.crypto_accounts.get(currency='BTC', is_default=True)
			success, txid, aux = referral_account.credit(settings.REFERRAL_BONUS)
			user.is_referrer_paid = txid
			user.save()
			referral_completed.send(sender=user, email=user.email, address=referral_account.address, txid=txid)
		except Exception:
			pass #loool
referral_completed.connect(check_referral)
