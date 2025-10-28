from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class Libro(models.Model):
    """Modelo para registrar libros de la biblioteca"""

    titulo = models.CharField(
        max_length=200, 
        verbose_name='Título',
        help_text='Ingrese el título completo del libro.'
    )
    autor = models.CharField(
        max_length=100, 
        verbose_name='Autor',
        help_text='Ingrese el nombre del autor del libro.'
    )
    isbn = models.CharField(
        max_length=13, 
        unique=True, 
        verbose_name='ISBN',
        help_text='Ingrese el código ISBN (13 caracteres).'
    )
    editorial = models.CharField(
        max_length=100, 
        null=True,
        blank=True,
        verbose_name='Editorial',
        help_text='Ingrese la editorial del libro (opcional).'
    )
    cantidad = models.PositiveIntegerField(
        default=1, 
        verbose_name='Cantidad',
        help_text='Ingrese la cantidad de ejemplares disponibles.'
    )
    numero_paginas = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='Número de páginas',
        help_text='Ingrese el número total de páginas (opcional).'
    )

    # Campos de auditoría
    fecha_registro = models.DateTimeField(
        'Fecha de registro', 
        auto_now_add=True
    )
    ultima_actualizacion = models.DateTimeField(
        'Última actualización', 
        auto_now=True
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='libros_registrados',
        verbose_name='Registrado por'
    )

    class Meta:
        verbose_name = 'Libro'
        verbose_name_plural = 'Libros'
        ordering = ['titulo']
    
    def __str__(self):
        return f"{self.titulo} - {self.autor}"


class PrestamoLibro(models.Model):
    """
    Modelo para registrar préstamos de libros
    
    IMPORTANTE: Este modelo NO maneja inventario automáticamente.
    El control de inventario se hace completamente desde GraphQL.
    """
    
    libro = models.ForeignKey(
        Libro,
        on_delete=models.CASCADE,
        related_name='prestamos',
        verbose_name='Libro',
        help_text='Seleccione el libro que será prestado.'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prestamos_libros',
        verbose_name='Usuario',
        help_text='Seleccione el usuario que tomará prestado el libro.'
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        verbose_name='Cantidad prestada',
        help_text='Ingrese la cantidad de ejemplares que se prestarán.'
    )
    fecha_prestamo = models.DateTimeField(
        'Fecha de préstamo', 
        auto_now_add=True
    )
    fecha_devolucion = models.DateField(
        'Fecha de devolución',
        null=True,
        blank=True,
        help_text='Ingrese la fecha en que el libro debe ser devuelto (opcional).'
    )
    prestado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prestamos_realizados',
        verbose_name='Prestado por',
        help_text='Usuario encargado de registrar el préstamo.'
    )
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devoluciones_recibidas',
        verbose_name='Recibido por',
        help_text='Usuario encargado de recibir la devolución (opcional).'
    )
    observaciones = models.TextField(
        blank=True, 
        verbose_name='Observaciones',
        help_text='Ingrese cualquier observación sobre el préstamo (opcional).'
    )
    devuelto = models.BooleanField(
        default=False,
        verbose_name='Devuelto',
        help_text='Indica si el libro ha sido devuelto.'
    )

    class Meta:
        verbose_name = 'Préstamo de Libro'
        verbose_name_plural = 'Préstamos de Libros'
        ordering = ['-fecha_prestamo']

    def __str__(self):
        return f"{self.libro.titulo} - {self.usuario.username} ({self.cantidad} ej.)"

    def clean(self):
        """Validaciones básicas del modelo"""
        super().clean()
        
        # Validar fechas
        if self.fecha_prestamo and self.fecha_devolucion:
            if self.fecha_devolucion < self.fecha_prestamo.date():
                raise ValidationError({
                    'fecha_devolucion': 
                    'La fecha de devolución no puede ser anterior a la fecha de préstamo.'
                })

        # Validar que la cantidad prestada no sea cero
        if self.cantidad <= 0:
            raise ValidationError({
                'cantidad': 'La cantidad prestada debe ser al menos 1.'
            })