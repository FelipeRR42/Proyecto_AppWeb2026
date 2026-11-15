from django.db import models
from django.conf import settings

# Create your models here.
class Usuario(models.Model):
    class Rol(models.TextChoices):
        PASAJERO = 'pasajero', 'Pasajero'
        ADMINISTRADOR = 'administrador', 'Administrador'

    cuenta = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = 'perfil',
        null=True,
        blank=True,
    )
    nombre_completo = models.CharField(max_length=200)
    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.PASAJERO,
    )
    telefono = models.CharField(max_length = 20, blank = True, default = '')
    direccion_retorno = models.CharField(
        max_length = 200, blank = True, default = ''
    )
    fecha_contratacion = models.DateField( null = True, blank = True)
    telefono_corporativo = models.CharField( max_length = 20, blank = True, default='')
    class Meta:
        db_table = 'Usuario'

    def __str__(self):
        return self.nombre_completo

"""
class Notificacion(models.Model):
    id_notificacion = models.AutoField(primary_key=True)
    id_admin = models.ForeignKey(Administrador, on_delete=models.CASCADE, db_column='id_admin')
    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Notificacion'

    def __str__(self):
        return self.titulo


class PasajeroRecibeNotificacion(models.Model):
    pasajero = models.ForeignKey(Pasajero, on_delete=models.CASCADE, db_column='id_pasajero')
    notificacion = models.ForeignKey(Notificacion, on_delete=models.CASCADE, db_column='id_notificacion')
    leido = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'Pasajero_recibe_Notificacion'
        unique_together = ('pasajero', 'notificacion')

    def __str__(self):
        return f"{self.pasajero} ← {self.notificacion}"
"""