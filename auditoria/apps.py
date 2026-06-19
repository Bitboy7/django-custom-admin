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
                UserProfile.objects.get_or_create(user=instance)

        # Sincronizar show_ui_builder desde la BD en el primer request
        # (no aquí para evitar acceso prematuro a la BD durante setup)
        from django.core.signals import request_started

        _applied = {'done': False}

        @receiver(request_started, weak=False)
        def _apply_jazzmin_ui_builder(sender, **kwargs):
            if _applied['done']:
                return
            try:
                from django.conf import settings
                from auditoria.models import SiteConfiguration
                cfg = SiteConfiguration.objects.filter(pk=1).values('show_ui_builder').first()
                if cfg is not None:
                    jazzmin = getattr(settings, 'JAZZMIN_SETTINGS', {})
                    jazzmin['show_ui_builder'] = cfg['show_ui_builder']
                _applied['done'] = True
            except Exception:
                pass
