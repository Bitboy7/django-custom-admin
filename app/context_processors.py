"""
Contexto global inyectado en todos los templates del admin.
Provee:
  - site_config_global : instancia de SiteConfiguration (singleton)
  - user_avatar_url    : URL del avatar del usuario autenticado
  - user_initials      : 2 iniciales del nombre (fallback al avatar)
  - user_display_name  : nombre completo o username
"""


def site_config(request):
    config = None
    try:
        from auditoria.models import SiteConfiguration
        config = SiteConfiguration.load()
    except Exception:
        pass

    avatar_url = ''
    user_initials = 'US'
    user_display = ''

    if request.user.is_authenticated:
        try:
            avatar_url = request.user.profile.avatar_url or ''
        except Exception:
            pass

        full_name = request.user.get_full_name().strip()
        if full_name:
            parts = full_name.split()
            if len(parts) >= 2:
                user_initials = (parts[0][0] + parts[-1][0]).upper()
            else:
                user_initials = parts[0][:2].upper()
        else:
            user_initials = request.user.username[:2].upper()

        user_display = full_name or request.user.username

    return {
        'site_config_global': config,
        'user_avatar_url': avatar_url,
        'user_initials': user_initials,
        'user_display_name': user_display,
    }
