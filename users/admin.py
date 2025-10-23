from django.contrib import admin
from .models import User
# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'rol', 'es_docente', 'nivel', 'fecha_registro')
    search_fields = ('username', 'first_name', 'last_name', 'dni')
    list_filter = ('rol', 'es_docente', 'nivel')