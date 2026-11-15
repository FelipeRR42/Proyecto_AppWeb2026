from django.conf import settings
from django.db import models


class Usuario(models.Model):
    class Rol(models.TextChoices):
        PASAJERO = 'pasajero', 'Pasajero'
        ADMINISTRADOR = 'administrador', 'Administrador'

    cuenta = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='perfil',
        primary_key=True,
    )
    nombre_completo = models.CharField(max_length=200)
    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.PASAJERO,
    )
    telefono = models.CharField(max_length=20, blank=True, default='')
    direccion_retorno = models.CharField(max_length=200, blank=True, default='')
    fecha_contratacion = models.DateField(null=True, blank=True)
    telefono_corporativo = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        db_table = 'Usuario'

    def __str__(self):
        return self.nombre_completo
