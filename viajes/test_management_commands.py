from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from usuarios.models import Usuario


class PoblarDatosPruebaTests(TestCase):
    @patch('viajes.management.commands.poblar_datos_prueba.get_mongo_db')
    def test_crea_cuentas_en_postgres_y_entidades_en_mongo(self, get_mongo_db):
        db = SimpleNamespace(
            command=MagicMock(),
            vehiculos=SimpleNamespace(find_one=MagicMock(return_value=None), replace_one=MagicMock()),
            viajes=SimpleNamespace(find_one=MagicMock(return_value=None), replace_one=MagicMock()),
            reservas=SimpleNamespace(find_one=MagicMock(return_value=None), replace_one=MagicMock()),
            notificaciones=SimpleNamespace(find_one=MagicMock(return_value=None), replace_one=MagicMock()),
        )
        get_mongo_db.return_value = db

        call_command('poblar_datos_prueba')

        profiles = list(Usuario.objects.select_related('cuenta').order_by('rol'))
        self.assertEqual(len(profiles), 7)
        self.assertEqual(
            sum(profile.rol == Usuario.Rol.ADMINISTRADOR for profile in profiles),
            1,
        )
        self.assertEqual(db.vehiculos.replace_one.call_count, 4)
        self.assertEqual(db.viajes.replace_one.call_count, 4)
        self.assertEqual(db.reservas.replace_one.call_count, 12)
        self.assertEqual(db.notificaciones.replace_one.call_count, 4)
        self.assertFalse(hasattr(db, 'usuarios'))
        notification = db.notificaciones.replace_one.call_args.args[1]
        self.assertTrue(all(
            isinstance(recipient['id_pasajero'], str)
            for recipient in notification['destinatarios']
        ))
