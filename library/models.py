from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class Libro(models.Model):
    """Modelo para registrar libros de la biblioteca"""

    titulo = models.CharField(max_length=200, verbose_name='Título')
    autor = models.CharField(max_length=100, verbose_name='Autor')
    isbn = models.CharField(max_length=13, unique=True, verbose_name='ISBN')
    editorial = models.CharField(max_length=100, verbose_name='Editorial')
    cantidad = models.PositiveIntegerField(default=1, verbose_name='Cantidad')
    numero_paginas = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='Número de páginas'
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
    """Modelo para registrar préstamos de libros"""
    
    libro = models.ForeignKey(
        Libro,
        on_delete=models.CASCADE,
        related_name='prestamos',
        verbose_name='Libro'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prestamos_libros',
        verbose_name='Usuario'
    )
    fecha_prestamo = models.DateTimeField('Fecha de préstamo', auto_now_add=True)
    fecha_devolucion = models.DateField('Fecha de devolución')
    prestado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prestamos_realizados',
        verbose_name='Prestado por'
    )
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devoluciones_recibidas',
        verbose_name='Recibido por'
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')

    class Meta:
        verbose_name = 'Préstamo de Libro'
        verbose_name_plural = 'Préstamos de Libros'
        ordering = ['-fecha_prestamo']

    def __str__(self):
        return f"{self.libro.titulo} - {self.usuario.username}"

    def clean(self):
        super().clean()
        
        # Validar fechas
        if self.fecha_prestamo and self.fecha_devolucion:
            if self.fecha_devolucion < self.fecha_prestamo.date():
                raise ValidationError({
                    'fecha_devolucion': 
                    'La fecha de devolución no puede ser anterior a la fecha de préstamo.'
                })

        # Validar disponibilidad del libro
        if self.libro.cantidad <= 0:
            raise ValidationError({
                'libro': 'No hay ejemplares disponibles de este libro.'
            })
