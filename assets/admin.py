from django.contrib import admin
from .models import Asset, AssetAssignment


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_inventario', 'tipo', 'estado', 'cantidad', 'ubicacion', 'responsable_actual')
    list_filter = ('tipo', 'estado')
    search_fields = ('nombre', 'codigo_inventario', 'ubicacion')
    ordering = ('nombre',)


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = ('bien', 'usuario', 'tipo_asignacion', 'estado', 'fecha_asignacion', 'fecha_devolucion_programada')
    list_filter = ('tipo_asignacion', 'estado')
    search_fields = ('bien__nombre', 'usuario__username', 'usuario__first_name', 'usuario__last_name')
    date_hierarchy = 'fecha_asignacion'
