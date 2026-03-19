from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuditoriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auditoria'
    verbose_name = _('Auditoría y Registro de Actividad')

    def ready(self):
        from django.db.models.signals import post_save
        from django.contrib.auth.models import User
        from django.dispatch import receiver
        from auditoria.models import UserProfile

        @receiver(post_save, sender=User, weak=False)
        def create_or_save_user_profile(sender, instance, created, **kwargs):
            if created:
                UserProfile.objects.get_or_create(user=instance)
            else:
                # create if doesn't exist (e.g. existing users on first deploy)
                UserProfile.objects.get_or_create(user=instance)
