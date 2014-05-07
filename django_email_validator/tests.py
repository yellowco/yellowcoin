# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.forms import EmailField
from django.utils.unittest import skip
from django.utils.unittest import TestCase
from django.test.simple import DjangoTestSuiteRunner


# A majority of these tests were stolen from Django's tests/regressiontests/forms/tests/fields.py

class FieldsTests(TestCase):
    def assertRaisesErrorWithMessage(self, error, message, callable, *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error, e:
            self.assertEqual(message, str(e))

    def test_emailfield_1(self):
        f = EmailField()
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(u'person@example.com', f.clean('person@example.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo@')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo@bar')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@invalid-.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@-invalid.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@inv-.alid-.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@inv-.-alid.com')
        self.assertEqual(u'example@django-cms.org', f.clean('example@django-cms.org'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@.com')


    def test_email_regexp_for_performance(self):
        f = EmailField()
        # Check for runaway regex security problem. This will take for-freeking-ever
        # if the security fix isn't in place.
        self.assertRaisesErrorWithMessage(
                ValidationError,
                "[u'Enter a valid e-mail address.']",
                f.clean,
                'viewx3dtextx26qx3d@yahoo.comx26latlngx3d15854521645943074058'
            )


    def test_emailfield_2(self):
        f = EmailField(required=False)
        self.assertEqual(u'', f.clean(''))
        self.assertEqual(u'', f.clean(None))
        self.assertEqual(u'person@example.com', f.clean('person@example.com'))
        self.assertEqual(u'example@example.com', f.clean('      example@example.com  \t   \t '))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo@')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo@bar')


    def test_emailfield_3(self):
        f = EmailField(min_length=10, max_length=15)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at least 10 characters (it has 9).']", f.clean, 'a@foo.com')
        self.assertEqual(u'alf@foo.com', f.clean('alf@foo.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at most 15 characters (it has 20).']", f.clean, 'alf123456788@foo.com')


    # http://idn.icann.org/E-mail_test
    @skip("Skipping IDN check")
    def test_emailfield_idn(self):
        f = EmailField()
        self.assertEqual(u'mailtest@مثال.إختبار', f.clean('mailtest@مثال.إختبار'))
        self.assertEqual(u'mailtest@例子.测试', f.clean('mailtest@例子.测试'))
        self.assertEqual(u'mailtest@例子.測試', f.clean('mailtest@例子.測試'))
        self.assertEqual(u'mailtest@παράδειγμα.δοκιμή', f.clean('mailtest@παράδειγμα.δοκιμή'))
        self.assertEqual(u'mailtest@उदाहरण.परीक्षा', f.clean('mailtest@उदाहरण.परीक्षा'))
        self.assertEqual(u'mailtest@例え.テスト', f.clean('mailtest@例え.テスト'))
        self.assertEqual(u'mailtest@실례.테스트', f.clean('mailtest@실례.테스트'))
        self.assertEqual(u'mailtest@مثال.آزمایشی', f.clean('mailtest@مثال.آزمایشی'))
        self.assertEqual(u'mailtest@пример.испытание', f.clean('mailtest@пример.испытание'))
        self.assertEqual(u'mailtest@உதாரணம்.பரிட்சை', f.clean('mailtest@உதாரணம்.பரிட்சை'))
        self.assertEqual(u'mailtest@בײַשפּיל.טעסט', f.clean('mailtest@בײַשפּיל.טעסט'))
        self.assertEqual(u'mailtest@xn--mgbh0fb.xn--kgbechtv', f.clean('mailtest@xn--mgbh0fb.xn--kgbechtv'))
        self.assertEqual(u'mailtest@xn--fsqu00a.xn--0zwm56d', f.clean('mailtest@xn--fsqu00a.xn--0zwm56d'))
        self.assertEqual(u'mailtest@xn--fsqu00a.xn--g6w251d', f.clean('mailtest@xn--fsqu00a.xn--g6w251d'))
        self.assertEqual(u'mailtest@xn--hxajbheg2az3al.xn--jxalpdlp', f.clean('mailtest@xn--hxajbheg2az3al.xn--jxalpdlp'))
        self.assertEqual(u'mailtest@xn--p1b6ci4b4b3a.xn--11b5bs3a9aj6g', f.clean('mailtest@xn--p1b6ci4b4b3a.xn--11b5bs3a9aj6g'))
        self.assertEqual(u'mailtest@xn--r8jz45g.xn--zckzah', f.clean('mailtest@xn--r8jz45g.xn--zckzah'))
        self.assertEqual(u'mailtest@xn--9n2bp8q.xn--9t4b11yi5a', f.clean('mailtest@xn--9n2bp8q.xn--9t4b11yi5a'))
        self.assertEqual(u'mailtest@xn--mgbh0fb.xn--hgbk6aj7f53bba', f.clean('mailtest@xn--mgbh0fb.xn--hgbk6aj7f53bba'))
        self.assertEqual(u'mailtest@xn--e1afmkfd.xn--80akhbyknj4f', f.clean('mailtest@xn--e1afmkfd.xn--80akhbyknj4f'))
        self.assertEqual(u'mailtest@xn--zkc6cc5bi7f6e.xn--hlcj6aya9esc7a', f.clean('mailtest@xn--zkc6cc5bi7f6e.xn--hlcj6aya9esc7a'))
        self.assertEqual(u'mailtest@xn--fdbk5d8ap9b8a8d.xn--deba0ad', f.clean('mailtest@xn--fdbk5d8ap9b8a8d.xn--deba0ad'))

