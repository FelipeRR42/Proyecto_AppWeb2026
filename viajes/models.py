from django.db import models

# Create your models here.

class Viaje(models.Model):
    id_viaje = models.AutoField(primary_key=True)
    id_admin = models.ForeignKey('usuarios.Administrador', on_delete=models.CASCADE, db_column='id_admin')
    patente_vehiculo = models.ForeignKey('Vehiculo', on_delete=models.CASCADE, db_column='patente')
    origen = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    fecha_evento = models.DateTimeField()
    fecha_salida = models.DateTimeField()
    fecha_retorno = models.DateTimeField()
    precio_ida_y_vuelta = models.IntegerField()
    precio_ida = models.IntegerField()
    estado = models.CharField(
        max_length=20, 
        choices=[('programado', 'Programado'),
                ('lleno', 'Lleno'),
                ('finalizado', 'Finalizado'),
                ('cancelado', 'Cancelado')]
    )
    recinto = models.CharField(max_length=100)
    artista = models.CharField(max_length=100)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()

    class Meta:
        db_table = 'Viaje'

    def __str__(self):
        return f"Viaje {self.id_viaje} - {self.origen} a {self.destino}"

class Vehiculo(models.Model):
    patente = models.CharField(primary_key=True, max_length=20)
    modelo = models.CharField(max_length=50)
    capacidad_maxima = models.IntegerField()

    class Meta:
        db_table = 'Vehiculo'

    def __str__(self):
        return f"Vehiculo {self.patente} - Modelo: {self.modelo}"