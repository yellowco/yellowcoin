import django.core.validators
import django.forms.fields
import django.db.models.fields

from django.utils.translation import ugettext_lazy as _

from validators import EmailValidator, email_re


__version__ = '0.1.1'

__all__ = ()


# Replace the existing regex with one that supports (encoded) IDN TLDs.
# The the local-part of the address is assumed to be ASCII, as the IETF EAI group has
# yet to complete the RFCs that define what this will look like in the future.
django.core.validators.email_re = email_re


# Replace the existing validator with one that performs DNS checks on the
# domain to attempt to test its legitimacy.
django.core.validators.validate_email = EmailValidator(
    _(u'Enter a valid e-mail address.'),
    'invalid'
)


# Depending on the loading order of various things, the EmailFields occasionally pick
# up the original validator before we can patch ours in. Let's take care of that.
django.forms.fields.EmailField.default_validators = [django.core.validators.validate_email]
django.db.models.fields.EmailField.default_validators = [django.core.validators.validate_email]

