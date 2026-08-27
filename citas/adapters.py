from django.conf import settings
from django.contrib.auth.models import User

from allauth.account.utils import perform_login
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp

from .models import PerfilCliente, Negocio


class PetNexoSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_app(self, request, provider, client_id=None):
        """Use the environment-backed Google app as the single OAuth source.

        Older installations may still have one or more Google ``SocialApp``
        records created through Django admin.  django-allauth combines those
        records with the app configured in settings, which raises
        ``MultipleObjectsReturned``.  PetNexo stores the deployment-specific
        OAuth credentials in environment variables, so that configuration is
        intentionally preferred whenever it is complete.
        """
        if provider == 'google' and settings.GOOGLE_LOGIN_CONFIGURED:
            return SocialApp(
                provider='google',
                name='Google OAuth (environment)',
                client_id=settings.GOOGLE_CLIENT_ID,
                secret=settings.GOOGLE_CLIENT_SECRET,
                key='',
            )
        return super().get_app(request, provider, client_id=client_id)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        PerfilCliente.objects.get_or_create(
            usuario=user,
            defaults={'negocio': Negocio.objects.filter(activo=True).order_by('id').first()},
        )
        return user

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        verified_email = self._get_verified_email(sociallogin)
        if not verified_email:
            return

        users = User.objects.filter(email__iexact=verified_email)
        if users.count() != 1:
            return
        user = users.first()

        sociallogin.connect(request, user)
        PerfilCliente.objects.get_or_create(
            usuario=user,
            defaults={'negocio': Negocio.objects.filter(activo=True).order_by('id').first()},
        )
        response = perform_login(
            request,
            user,
            email_verification='none',
            redirect_url=settings.LOGIN_REDIRECT_URL,
        )
        raise ImmediateHttpResponse(response)

    def _get_verified_email(self, sociallogin):
        for email_address in sociallogin.email_addresses:
            if email_address.verified:
                return email_address.email
        email = getattr(sociallogin.user, 'email', '')
        return email or None
