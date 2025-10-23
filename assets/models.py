from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class Asset(models.Model):
    """Modelo para registrar los bienes del colegio."""

    # ======================
    # OPCIONES DE ELECCIÓN
    # ======================
    TIPOS_BIEN = (
        ('MOVIL', 'Bien Móvil'),
        ('INMOVIL', 'Bien Inmóvil'),
    )

    ESTADOS_BIEN = (
        ('DISPONIBLE', 'Disponible'),
        ('EN_USO', 'En uso'),
        ('DANADO', 'Dañado'),
        ('BAJA', 'Dado de baja'),
    )

    # ======================
    # CAMPOS PRINCIPALES
    # ======================
    nombre = models.CharField(
        'Nombre del bien',
        max_length=200,
        help_text='Nombre identificativo del bien, por ejemplo: “Mesa de madera” o “Proyector Epson X200”.'
    )
    descripcion = models.TextField(
        'Descripción',
        blank=True,
        help_text='Detalles adicionales sobre el bien, su estado físico o características.'
    )
    tipo = models.CharField(
        'Tipo',
        max_length=20,
        choices=TIPOS_BIEN,
        help_text='Indica si el bien es móvil (puede trasladarse) o inmóvil (instalado permanentemente).'
    )
    codigo_inventario = models.CharField(
        'Código de inventario',
        max_length=50,
        unique=True,
        help_text='Código único de inventario para identificar el bien o grupo de bienes.'
    )
    cantidad = models.PositiveIntegerField(
        'Cantidad',
        default=1,
        help_text='Número total de unidades de este bien (por ejemplo: 5 mesas o 10 sillas).'
    )
    ubicacion = models.CharField(
        'Ubicación',
        max_length=200,
        blank=True,
        null=True,
        help_text='Lugar físico donde se encuentra el bien o grupo de bienes.'
    )
    fecha_adquisicion = models.DateField(
        'Fecha de adquisición',
        help_text='Fecha en la que el bien fue adquirido.'
    )
    estado = models.CharField(
        'Estado',
        max_length=20,
        choices=ESTADOS_BIEN,
        default='DISPONIBLE',
        help_text='Situación actual del bien: disponible, en uso, dañado o dado de baja.'
    )

    # ======================
    # RELACIONES
    # ======================
    responsable_actual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bienes_asignados',
        verbose_name='Responsable actual',
        help_text='Usuario que actualmente tiene el bien bajo su responsabilidad.'
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bienes_registrados',
        verbose_name='Registrado por',
        help_text='Usuario del sistema que registró este bien.'
    )

    # ======================
    # IMAGEN Y AUDITORÍA
    # ======================
    imagen = models.ImageField(
        'Imagen',
        upload_to='bienes/',
        blank=True,
        null=True,
        help_text='Fotografía del bien (opcional).'
    )
    fecha_registro = models.DateTimeField(
        'Fecha de registro',
        auto_now_add=True,
        help_text='Fecha en la que el bien fue registrado en el sistema.'
    )
    ultima_actualizacion = models.DateTimeField(
        'Última actualización',
        auto_now=True,
        help_text='Fecha de la última modificación del registro.'
    )

    # ======================
    # MÉTODOS
    # ======================
    def __str__(self):
        return f"{self.nombre} ({self.codigo_inventario}) x{self.cantidad}"

    def esta_disponible(self):
        """Verifica si el bien está disponible para asignar."""
        return (
            self.responsable_actual is None
            and self.estado == 'DISPONIBLE'
            and self.cantidad > 0
        )

    class Meta:
        verbose_name = "Bien"
        verbose_name_plural = "Bienes"
        ordering = ['nombre']


class AssetAssignment(models.Model):
    """Modelo para registrar el historial de asignaciones y préstamos de bienes."""

    # ======================
    # OPCIONES DE ELECCIÓN
    # ======================
    TIPOS_ASIGNACION = (
        ('PRESTAMO', 'Préstamo temporal'),
        ('ASIGNACION', 'Asignación permanente'),
    )

    ESTADOS_ASIGNACION = (
        ('ACTIVA', 'Activa'),
        ('DEVUELTO', 'Devuelto'),
        ('TRANSFERIDO', 'Transferido'),
    )

    # ======================
    # RELACIONES
    # ======================
    bien = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='historial_asignaciones',
        verbose_name='Bien',
        help_text='Bien que se asigna o presta al usuario.'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='historial_bienes',
        verbose_name='Usuario',
        help_text='Usuario que recibe el bien asignado o en préstamo.'
    )

    # ======================
    # INFORMACIÓN DE LA ASIGNACIÓN
    # ======================
    tipo_asignacion = models.CharField(
        'Tipo de asignación',
        max_length=20,
        choices=TIPOS_ASIGNACION,
        help_text='Indica si se trata de un préstamo temporal o una asignación permanente.'
    )
    cantidad_asignada = models.PositiveIntegerField(
        'Cantidad asignada',
        default=1,
        help_text='Número de unidades del bien que se asignan al usuario.'
    )
    estado = models.CharField(
        'Estado',
        max_length=20,
        choices=ESTADOS_ASIGNACION,
        default='ACTIVA',
        help_text='Estado actual de la asignación: activa, devuelto o transferido.'
    )
    observaciones = models.TextField(
        'Observaciones',
        blank=True,
        help_text='Notas o comentarios adicionales sobre esta asignación.'
    )

    # ======================
    # FECHAS
    # ======================
    fecha_asignacion = models.DateTimeField(
        'Fecha de asignación',
        auto_now_add=True,
        help_text='Fecha y hora en que se realizó la asignación del bien.'
    )
    fecha_devolucion_programada = models.DateField(
        'Fecha de devolución programada',
        blank=True,
        null=True,
        help_text='Fecha prevista para la devolución (solo para préstamos temporales).'
    )
    fecha_devolucion_real = models.DateTimeField(
        'Fecha de devolución real',
        blank=True,
        null=True,
        help_text='Fecha y hora en que el bien fue efectivamente devuelto.'
    )

    # ======================
    # USUARIO RESPONSABLE DE LA ASIGNACIÓN
    # ======================
    asignado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='asignaciones_realizadas',
        verbose_name='Asignado por',
        help_text='Usuario del sistema que realizó la asignación del bien.'
    )

    # ======================
    # VALIDACIONES
    # ======================
    def clean(self):
        """Evita asignar más cantidad de la disponible."""
        if self.cantidad_asignada > self.bien.cantidad:
            raise ValidationError("No se puede asignar más cantidad de la disponible.")

    # ======================
    # MÉTODOS
    # ======================
    def save(self, *args, **kwargs):
        """Guarda la asignación y actualiza el estado del bien automáticamente."""
        super().save(*args, **kwargs)

        bien = self.bien
        if self.estado == 'ACTIVA':
            bien.estado = 'EN_USO'
            bien.responsable_actual = self.usuario
        elif self.estado in ['DEVUELTO', 'TRANSFERIDO']:
            bien.estado = 'DISPONIBLE'
            bien.responsable_actual = None
        bien.save()

    def devolver(self):
        """Marca la asignación como devuelta y actualiza el bien."""
        self.estado = 'DEVUELTO'
        self.fecha_devolucion_real = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.bien.nombre} → {self.usuario.get_full_name()} ({self.get_estado_display()})"

    class Meta:
        verbose_name = 'Asignación de Bien'
        verbose_name_plural = 'Asignaciones de Bienes'
        ordering = ['-fecha_asignacion']
