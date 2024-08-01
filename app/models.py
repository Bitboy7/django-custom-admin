from django.contrib.auth.models import User
from django.db import models

class User(User):
    # Aquí puedes agregar campos adicionales o modificar los existentes
    # por ejemplo:
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
