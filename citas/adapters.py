from django.conf import settings
from django.contrib.auth.models import User

from allauth.account.utils import perform_login
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import PerfilCliente, Negocio


class PetNexoSocialAccountAdapter(DefaultSocialAccountAdapter):
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

        user = User.objects.filter(email__iexact=verified_email).first()
        if not user:
            return

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
