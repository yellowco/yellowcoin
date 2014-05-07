import re

import dns.resolver

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.core.validators import validate_email

__all__ = (
    'email_re',
    'EmailValidator',
)


email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"'  # quoted-string
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)$', re.IGNORECASE)  # domain


class EmailValidator(EmailValidator):
    def __call__(self, value):
        super(EmailValidator, self).__call__(value)

        try:
            local_part, domain = value.split(u'@', 1)
            answer = dns.resolver.query(domain, 'MX')
        except dns.resolver.NXDOMAIN:
            # Domain doesn't exist.
            raise ValidationError(self.message, code=self.code)
        except dns.resolver.NoAnswer:
            # Domain exists, but no MX records, try for an A.
            try:
                answer = dns.resolver.query(domain, 'A')
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                # No A record either; domain not suitable for email.
                raise ValidationError(self.message, code=self.code)
            except:
                # Either a timeout or a DNS server error occurred. Not indicative
                # of a bad domain. Assume good.
                pass
        except:
            # Either a timeout or a DNS server error occurred. Not indicative
            # of a bad domain. Assume good.
            pass

