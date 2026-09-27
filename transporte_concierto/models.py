from django.db import models


class Pasajero(models.Model):
    id_pasajero = models.AutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    correo_electronico = models.EmailField(unique=True)
    contrasenia = models.CharField(max_length=128)  # se guarda hasheada, nunca en texto plano

    class Meta:
        db_table = 'Pasajero'

    def __str__(self):
        return self.nombre_completo


class Administrador(models.Model):
    id_admin = models.AutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=200)
    correo_electronico = models.EmailField(unique=True)
    contrasenia = models.CharField(max_length=128)

    class Meta:
        db_table = 'Administrador'

    def __str__(self):
        return self.nombre_completo


class Notificacion(models.Model):
    id_notificacion = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField()

    class Meta:
        db_table = 'Notificacion'

    def __str__(self):
        return self.titulo


class PasajeroRecibeNotificacion(models.Model):
    pasajero = models.ForeignKey(Pasajero, on_delete=models.CASCADE, db_column='id_pasajero')
    notificacion = models.ForeignKey(Notificacion, on_delete=models.CASCADE, db_column='id_notificacion')

    class Meta:
        db_table = 'Pasajero_recibe_Notificacion'
        unique_together = ('pasajero', 'notificacion')

    def __str__(self):
        return f"{self.pasajero} ← {self.notificacion}"


class ViajeAConcierto(models.Model):
    id_viaje = models.AutoField(primary_key=True)
    administrador = models.ForeignKey(
        Administrador, on_delete=models.CASCADE, db_column='id_admin', related_name='viajes'
    )
    fecha_viaje = models.DateTimeField()
    descripcion = models.TextField(null=True, blank=True)
    recinto = models.CharField(max_length=200)
    estado = models.CharField(max_length=50)
    titulo = models.CharField(max_length=200)
    direccion_origen = models.CharField(max_length=255)
    direccion_destino = models.CharField(max_length=255)
    vehiculos = models.ManyToManyField(
        'Vehiculo', through='ViajeUsaVehiculo', related_name='viajes'
    )

    class Meta:
        db_table = 'Viaje_a_concierto'

    def __str__(self):
        return self.titulo


class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    pasajero = models.ForeignKey(
        Pasajero, on_delete=models.CASCADE, db_column='id_pasajero', related_name='reservas'
    )
    viaje = models.ForeignKey(
        ViajeAConcierto, on_delete=models.CASCADE, db_column='id_viaje', related_name='reservas'
    )
    fecha_reserva = models.DateTimeField()
    tipo_viaje = models.CharField(max_length=50)
    estado = models.CharField(max_length=50)

    class Meta:
        db_table = 'Reserva'

    def __str__(self):
        return f"Reserva #{self.id_reserva} - {self.pasajero}"


class AsientoReserva(models.Model):
    numero_asiento = models.PositiveIntegerField(db_column='asientos_reserva')
    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE, db_column='id_reserva', related_name='asientos'
    )

    class Meta:
        db_table = 'asientos_reserva'
        unique_together = ('numero_asiento', 'reserva')
        constraints = [
            models.CheckConstraint(condition=models.Q(numero_asiento__gt=0), name='asiento_numero_positivo'),
        ]

    def __str__(self):
        return f"Asiento {self.numero_asiento} - Reserva #{self.reserva_id}"


class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    reserva = models.OneToOneField(
        Reserva, on_delete=models.CASCADE, db_column='id_reserva', related_name='pago'
    )
    monto = models.PositiveIntegerField()
    estado = models.CharField(max_length=50)

    class Meta:
        db_table = 'Pago'
        constraints = [
            models.CheckConstraint(condition=models.Q(monto__gt=0), name='pago_monto_positivo'),
        ]

    def __str__(self):
        return f"Pago #{self.id_pago} - {self.estado}"


class Vehiculo(models.Model):
    patente = models.CharField(max_length=10, primary_key=True)
    modelo = models.CharField(max_length=100)
    capacidad_maxima = models.PositiveIntegerField()

    class Meta:
        db_table = 'Vehiculo'
        constraints = [
            models.CheckConstraint(condition=models.Q(capacidad_maxima__gt=0), name='vehiculo_capacidad_positiva'),
        ]

    def __str__(self):
        return f"{self.patente} ({self.modelo})"


class ViajeUsaVehiculo(models.Model):
    viaje = models.ForeignKey(ViajeAConcierto, on_delete=models.CASCADE, db_column='id_viaje')
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, db_column='patente')

    class Meta:
        db_table = 'Viaje_a_concierto_usa_Vehiculo'
        unique_together = ('viaje', 'vehiculo')

    def __str__(self):
        return f"{self.viaje} usa {self.vehiculo}"