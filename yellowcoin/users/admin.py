from django import forms
from django.http import HttpResponse
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.template import RequestContext
from django.template.loader import render_to_string
from yellowcoin.users.models import User, Profile

class UserCreationForm(forms.ModelForm):
	"""A form for creating new users. Includes all the required
	fields, plus a repeated password."""
	password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
	password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

	class Meta:
		model = User
		fields = ('email', 'is_active', 'is_staff', 'is_superuser')

	def clean_password2(self):
		# Check that the two password entries match
		password1 = self.cleaned_data.get("password1")
		password2 = self.cleaned_data.get("password2")
		if password1 and password2 and password1 != password2:
			raise forms.ValidationError("Passwords don't match")
		return password2

	def save(self, commit=True):
		# Save the provided password in hashed format
		user = super(UserCreationForm, self).save(commit=False)
		user.set_password(self.cleaned_data["password1"])
		if commit:
			user.save()
		return user


class UserChangeForm(forms.ModelForm):
	"""A form for updating users. Includes all the fields on
	the user, but replaces the password field with admin's
	password hash display field.
	"""
	password = ReadOnlyPasswordHashField(label="Password",
		help_text="Raw passwords are not stored, so there is no way to see this user's password, but you can change the password using <a href=\"password/\">this form</a>.")

	class Meta:
		model = User
		fields = ['email', 'password', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']

	def clean_password(self):
		# Regardless of what the user provides, return the initial value.
		# This is done here, rather than on the field, because the
		# field does not have access to the initial value
		return self.initial["password"]

class ProfileInline(admin.StackedInline):
	model = Profile
	can_delete = False
	verbose_name_plural = "profile"

class CustomUserAdmin(UserAdmin):
	# The forms to add and change user instances
	form = UserChangeForm
	add_form = UserCreationForm

	# The fields to be used in displaying the User model.
	# These override the definitions on the base UserAdmin
	# that reference specific fields on auth.User.
	list_display = ('email', 'is_staff')
	list_filter = ('is_staff', 'is_superuser', 'is_active',)
	fieldsets = (
		(None, {'fields': ('email', 'password')}),
		('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
		('Information', {'fields': ('date_joined', 'last_login',)}),
	)
	# add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
	# overrides get_fieldsets to use this attribute when creating a user.
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ('email', 'password1', 'password2')}
		),
	)
	readonly_fields = ('date_joined', 'last_login',)
	search_fields = ('email',)
	ordering = ['id']
	filter_horizontal = ()
	inlines = (ProfileInline,)
	actions = ['users_to_csv', 'resend_activation_email']

	def users_to_csv(model_admin, request, users):
		response = HttpResponse(content_type='text/plain')
		for user in users:
			response.write(user.email + '\n')
		return response
	users_to_csv.short_description = 'Export user emails to CSV'

# Now register the new UserAdmin...
admin.site.register(User, CustomUserAdmin)
