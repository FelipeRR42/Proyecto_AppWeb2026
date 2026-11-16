from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def reject_duplicate_emails(apps, schema_editor):
    table_name = schema_editor.quote_name('auth_user')
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT LOWER(email)
            FROM {table_name}
            GROUP BY LOWER(email)
            HAVING COUNT(*) > 1
            LIMIT 1
            '''
        )
        if cursor.fetchone():
            raise RuntimeError(
                'auth_user contiene correos duplicados sin distinguir mayúsculas. '
                'Corrígelos antes de aplicar esta migración.'
            )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(reject_duplicate_emails, migrations.RunPython.noop),
        migrations.RunSQL(
            sql=(
                'CREATE UNIQUE INDEX auth_user_email_ci_unique '
                'ON auth_user (LOWER(email))'
            ),
            reverse_sql='DROP INDEX auth_user_email_ci_unique',
        ),
        migrations.AlterField(
            model_name='usuario',
            name='cuenta',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                primary_key=True,
                related_name='perfil',
                serialize=False,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
