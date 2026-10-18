from django.db import models

# Create your models here.
class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=200)
    correo_electronico = models.EmailField(unique=True)
    contrasenia = models.CharField(max_length=128)  # se guarda hasheada, nunca en texto plano

    class Meta:
        db_table = 'Usuario'

    def __str__(self):
        return self.nombre_completo


class Pasajero(Usuario):
    id_pasajero = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True, parent_link=True)
    direccion_retorno_predeterminada = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)

    class Meta:
        db_table = 'Pasajero'

    def __str__(self):
        return self.nombre_completo


class Administrador(Usuario):
    id_admin = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True, parent_link=True)
    fecha_contratacion = models.DateField()
    telefono_corporativo = models.CharField(max_length=20)

    class Meta:
        db_table = 'Administrador'

    def __str__(self):
        return self.nombre_completo


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
