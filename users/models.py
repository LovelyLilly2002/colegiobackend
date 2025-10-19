from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # ====== OPCIONES DE ELECCIÓN ======
    ROLES = (
        ('ADMIN', 'Administrador'),
        ('BIENES', 'Responsable de Bienes'),
        ('BIBLIOTECA', 'Responsable de Biblioteca'),
        ('GENERAL', 'Usuario General'),
    )

    NIVELES = (
        ('INICIAL', 'Inicial'),
        ('PRIMARIA', 'Primaria'),
        ('SECUNDARIA', 'Secundaria'),
    )

    TURNOS = (
        ('MAÑANA', 'Mañana'),
        ('TARDE', 'Tarde'),
    )

    # ====== CAMPOS DEL USUARIO ======
    nombre = models.CharField('Nombre', max_length=100, help_text='Nombre del usuario o docente.')
    apellidos = models.CharField('Apellidos', max_length=100, help_text='Apellidos completos del usuario.')
    dni = models.CharField('DNI', max_length=8, unique=True, blank=True, null=True, help_text='Documento Nacional de Identidad (8 dígitos).')
    telefono = models.CharField('Teléfono', max_length=15, blank=True, null=True, help_text='Número de teléfono de contacto.')
    rol = models.CharField(max_length=20, choices=ROLES, default='GENERAL', help_text='Rol o tipo de usuario dentro del sistema.')
    es_docente = models.BooleanField('Es docente', default=False, help_text='Marcar si el usuario pertenece al personal docente.')
    grado = models.CharField('Grado', max_length=10, blank=True, null=True, help_text='Grado que enseña el docente (si aplica).')
    seccion = models.CharField('Sección', max_length=10, blank=True,null=True,  help_text='Sección a cargo del docente.')
    turno = models.CharField('Turno', max_length=20, choices=TURNOS, blank=True,null=True, help_text='Turno en el que trabaja el docente.')
    nivel = models.CharField('Nivel', max_length=20, choices=NIVELES, blank=True,null=True, help_text='Nivel educativo donde enseña el docente.')

    # ====== CAMPOS DE AUDITORÍA ======
    fecha_registro = models.DateTimeField('Fecha de registro', auto_now_add=True, help_text='Fecha en la que el usuario fue creado en el sistema.')
    ultima_actualizacion = models.DateTimeField('Última actualización', auto_now=True, help_text='Fecha de la última modificación del usuario.')

    # ====== CONFIGURACIÓN META ======
    class Meta:
        verbose_name = 'Usuario'               # Cómo se mostrará en el panel de administración
        verbose_name_plural = 'Usuarios'       # Versión plural del nombre
        ordering = ['-fecha_registro']         # Orden de los registros (los más nuevos primero)

    # ====== REPRESENTACIÓN DEL USUARIO ======
    def __str__(self):
        # Devuelve cómo se mostrará el usuario al imprimirlo o en el panel admin
        return f"{self.username} ({self.get_rol_display()})"

    # ====== MÉTODOS PERSONALIZADOS ======
    def get_nombre_completo(self):
        """Retorna el nombre completo del usuario."""
        return f"{self.nombre} {self.apellidos}"

    def puede_gestionar_bienes(self):
        """Verifica si el usuario tiene permiso para gestionar bienes."""
        return self.rol in ['ADMIN', 'BIENES']

    def puede_gestionar_biblioteca(self):
        """Verifica si el usuario tiene permiso para gestionar la biblioteca."""
        return self.rol in ['ADMIN', 'BIBLIOTECA']

    def es_administrador(self):
        """Verifica si el usuario es administrador."""
        return self.rol == 'ADMIN'
