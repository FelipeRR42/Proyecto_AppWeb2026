from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Comando retirado: las cuentas y perfiles ahora pertenecen a PostgreSQL.'

    def handle(self, *args, **options):
        raise CommandError(
            'Este migrador pertenece al esquema anterior y ya no se puede usar. '
            'No migres usuarios a MongoDB; los usuarios y sus roles viven en PostgreSQL. '
            'Para cargar datos demo, ejecuta poblar_datos_prueba.'
        )
