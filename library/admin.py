from django.contrib import admin
from .models import Libro, PrestamoLibro

@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'isbn', 'editorial', 'cantidad', 'fecha_registro')
    search_fields = ('titulo', 'autor', 'isbn')
    list_filter = ('editorial',)
    ordering = ('titulo',)

@admin.register(PrestamoLibro)
class PrestamoLibroAdmin(admin.ModelAdmin):
    list_display = ('libro', 'usuario', 'fecha_prestamo', 'fecha_devolucion', 'prestado_por', 'recibido_por')
    search_fields = ('libro__titulo', 'usuario__username')
    list_filter = ('fecha_prestamo', 'fecha_devolucion')
