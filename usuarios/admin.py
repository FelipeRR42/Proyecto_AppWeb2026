from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = (
        'cuenta',
        'nombre_completo',
        'rol',
        'telefono',
    )
    list_filter = ('rol',)
    search_fields = (
        'nombre_completo',
        'cuenta__username',
        'cuenta__email',
    )
