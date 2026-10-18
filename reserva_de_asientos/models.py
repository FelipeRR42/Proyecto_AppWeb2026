from django.db import models

# Create your models here.

class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    id_pasajero = models.ForeignKey('usuarios.Pasajero', on_delete=models.CASCADE, db_column='id_pasajero')
    id_viaje = models.ForeignKey('viajes.Viaje', on_delete=models.CASCADE, db_column='id_viaje', null=True, blank=True)
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20)
    tipo_viaje = models.CharField(max_length=20, choices=[('ida', 'Ida'), ('ida_vuelta', 'Ida y Vuelta')])
    direccion_retorno = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'Reserva'

    def __str__(self):
        return f"Reserva {self.id_reserva} - Pasajero {self.id_pasajero.nombre_completo}"

class AsientoViaje(models.Model):
    id_asiento = models.AutoField(primary_key=True)
    num_asiento = models.PositiveSmallIntegerField()
    id_reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, db_column='id_reserva', null=True, blank=True)
    id_viaje = models.ForeignKey('viajes.Viaje', on_delete=models.CASCADE, db_column='id_viaje')
    estado_asiento = models.CharField(max_length=20, 
        choices=[('disponible', 'Disponible'), 
            ('ocupado', 'Ocupado'), 
            ('bloqueado', 'Bloqueado')]
        )

    rut_ocupante = models.CharField(max_length=20, null=True, blank=True)
    nombre_ocupante = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'AsientoViaje'
        constraints = [ models.UniqueConstraint(fields=['id_viaje', 'num_asiento'], name='un_asiento_por_viaje') ]

    def __str__(self):
        return f"Asiento {self.num_asiento} - Viaje {self.id_viaje.id_viaje}"

class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    id_reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, db_column='id_reserva')
    id_transaccion = models.CharField(max_length=100, unique=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=50)
    estado = models.CharField(
        max_length=20, 
        choices=[('pendiente', 'Pendiente'), 
                ('completado', 'Completado'), 
                ('fallido', 'Fallido'), 
                ('reembolsado', 'Reembolsado')]
                )

    class Meta:
        db_table = 'Pago'

    def __str__(self):
        return f"Pago {self.id_pago} - Reserva {self.id_reserva.id_reserva}"