import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from .models import Libro, PrestamoLibro


# =====================================================
#  TIPOS (GraphQL Types)
# =====================================================
class LibroType(DjangoObjectType):
    """Tipo GraphQL que representa el modelo Libro"""
    class Meta:
        model = Libro
        fields = "__all__"


class UsuarioType(DjangoObjectType):
    """Tipo GraphQL para el modelo User"""
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "first_name", "last_name")


class PrestamoLibroType(DjangoObjectType):
    """Tipo GraphQL que representa el modelo PrestamoLibro con información completa"""
    libro = graphene.Field(LibroType)
    usuario = graphene.Field(UsuarioType)
    prestado_por = graphene.Field(UsuarioType)
    recibido_por = graphene.Field(UsuarioType)
    
    class Meta:
        model = PrestamoLibro
        fields = "__all__"


# =====================================================
#  QUERIES (Consultas de lectura)
# =====================================================
class Query(graphene.ObjectType):
    libros = graphene.List(LibroType)
    libros_disponibles = graphene.List(LibroType)
    prestamos = graphene.List(PrestamoLibroType)
    libro_por_id = graphene.Field(LibroType, id=graphene.Int(required=True))
    prestamos_por_usuario = graphene.List(PrestamoLibroType, usuario_id=graphene.Int(required=True))
    mis_prestamos = graphene.List(PrestamoLibroType)
    prestamos_activos_por_usuario = graphene.List(PrestamoLibroType, usuario_id=graphene.Int(required=True))

    @login_required
    def resolve_libros(root, info):
        """Devuelve todos los libros"""
        return Libro.objects.all()
    
    @login_required
    def resolve_libros_disponibles(root, info):
        """Devuelve solo los libros con ejemplares disponibles (cantidad > 0)."""
        return Libro.objects.filter(cantidad__gt=0)

    @login_required
    def resolve_prestamos(root, info):
        """Devuelve todos los préstamos con información de libro y usuario"""
        return PrestamoLibro.objects.select_related(
            "libro", "usuario", "prestado_por", "recibido_por"
        ).all().order_by('-fecha_prestamo')

    @login_required
    def resolve_libro_por_id(root, info, id):
        """Busca un libro por ID"""
        try:
            return Libro.objects.get(pk=id)
        except Libro.DoesNotExist:
            raise GraphQLError("Libro no encontrado.")

    @login_required
    def resolve_prestamos_por_usuario(root, info, usuario_id):
        """Devuelve todos los préstamos de un usuario específico (activos e históricos)"""
        return PrestamoLibro.objects.select_related(
            "libro", "usuario", "prestado_por", "recibido_por"
        ).filter(usuario_id=usuario_id).order_by('-fecha_prestamo')

    @login_required
    def resolve_prestamos_activos_por_usuario(root, info, usuario_id):
        """Devuelve solo los préstamos activos (no devueltos) de un usuario"""
        return PrestamoLibro.objects.select_related(
            "libro", "usuario", "prestado_por"
        ).filter(usuario_id=usuario_id, devuelto=False).order_by('-fecha_prestamo')

    @login_required
    def resolve_mis_prestamos(self, info):
        """Devuelve los préstamos del usuario autenticado"""
        user = info.context.user
        return PrestamoLibro.objects.select_related(
            "libro", "prestado_por", "recibido_por"
        ).filter(usuario=user).order_by('-fecha_prestamo')


# =====================================================
#  MUTACIONES PARA LIBROS
# =====================================================
class AgregarLibro(graphene.Mutation):
    """Agrega un nuevo libro"""
    libro = graphene.Field(LibroType)

    class Arguments:
        titulo = graphene.String(required=True)
        autor = graphene.String(required=True)
        isbn = graphene.String(required=True)
        editorial = graphene.String(required=False)
        cantidad = graphene.Int(required=True)
        numero_paginas = graphene.Int(required=False)

    @login_required
    def mutate(self, info, titulo, autor, isbn, editorial=None, cantidad=1, numero_paginas=None):
        user = info.context.user

        if Libro.objects.filter(isbn=isbn).exists():
            raise GraphQLError("Ya existe un libro con este ISBN.")

        libro = Libro.objects.create(
            titulo=titulo,
            autor=autor,
            isbn=isbn,
            editorial=editorial,
            cantidad=cantidad or 1,
            numero_paginas=numero_paginas,
            registrado_por=user
        )
        return AgregarLibro(libro=libro)


class SumarCantidadLibro(graphene.Mutation):
    """Suma o resta cantidad de ejemplares de un libro"""
    libro = graphene.Field(LibroType)

    class Arguments:
        id = graphene.ID(required=True)
        cantidad_delta = graphene.Int(required=True)

    @login_required
    def mutate(self, info, id, cantidad_delta):
        try:
            libro = Libro.objects.get(pk=id)
        except Libro.DoesNotExist:
            raise GraphQLError("El libro no existe.")

        libro.cantidad += cantidad_delta
        if libro.cantidad < 0:
            libro.cantidad = 0
        libro.save()

        return SumarCantidadLibro(libro=libro)


class EliminarCantidadLibro(graphene.Mutation):
    """Resta cantidad; si llega a 0, elimina el libro"""
    libro = graphene.Field(LibroType)
    eliminado = graphene.Boolean()

    class Arguments:
        id = graphene.ID(required=True)
        cantidad = graphene.Int(required=True)

    @login_required
    def mutate(self, info, id, cantidad):
        try:
            libro = Libro.objects.get(pk=id)
        except Libro.DoesNotExist:
            raise GraphQLError("El libro no existe.")

        if cantidad <= 0:
            raise GraphQLError("La cantidad debe ser mayor que 0.")

        libro.cantidad -= cantidad
        if libro.cantidad <= 0:
            libro.delete()
            return EliminarCantidadLibro(libro=None, eliminado=True)

        libro.save()
        return EliminarCantidadLibro(libro=libro, eliminado=False)


class ActualizarLibro(graphene.Mutation):
    """Actualiza información del libro"""
    libro = graphene.Field(LibroType)

    class Arguments:
        id = graphene.ID(required=True)
        titulo = graphene.String()
        autor = graphene.String()
        isbn = graphene.String()
        editorial = graphene.String()
        numero_paginas = graphene.Int()

    @login_required
    def mutate(self, info, id, **kwargs):
        try:
            libro = Libro.objects.get(pk=id)
        except Libro.DoesNotExist:
            raise GraphQLError("Libro no encontrado.")

        for key, value in kwargs.items():
            setattr(libro, key, value)
        libro.save()
        return ActualizarLibro(libro=libro)


# =====================================================
#  MUTACIONES PARA PRÉSTAMOS
# =====================================================
class CrearPrestamo(graphene.Mutation):
    """Crea un préstamo o incrementa uno existente"""
    prestamo = graphene.Field(PrestamoLibroType)
    mensaje = graphene.String()

    class Arguments:
        libro_id = graphene.ID(required=True)
        usuario_id = graphene.ID(required=True)
        cantidad = graphene.Int(required=True)
        fecha_devolucion = graphene.Date(required=False)
        observaciones = graphene.String(required=False)

    @login_required
    @transaction.atomic
    def mutate(self, info, libro_id, usuario_id, cantidad, fecha_devolucion=None, observaciones=None):
        User = get_user_model()
        prestado_por = info.context.user

        # Validaciones básicas
        if cantidad <= 0:
            raise GraphQLError("La cantidad debe ser mayor que 0.")

        try:
            libro = Libro.objects.select_for_update().get(pk=libro_id)
        except Libro.DoesNotExist:
            raise GraphQLError("El libro especificado no existe.")

        try:
            usuario = User.objects.get(pk=usuario_id)
        except User.DoesNotExist:
            raise GraphQLError("El usuario especificado no existe.")

        # Validar stock disponible
        if libro.cantidad < cantidad:
            raise GraphQLError(
                f"No hay suficientes ejemplares disponibles. "
                f"Solo quedan {libro.cantidad} y se necesitan {cantidad}."
            )

        # Buscar préstamo activo existente (sin devolver)
        prestamo_existente = PrestamoLibro.objects.filter(
            usuario=usuario,
            libro=libro,
            devuelto=False
        ).first()

        if prestamo_existente:
            # Incrementar préstamo existente
            prestamo_existente.cantidad += cantidad
            prestamo_existente.fecha_prestamo = timezone.now()
            
            if observaciones:
                if prestamo_existente.observaciones:
                    prestamo_existente.observaciones += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {observaciones}"
                else:
                    prestamo_existente.observaciones = observaciones
            
            prestamo_existente.save()
            
            # Restar del inventario
            libro.cantidad -= cantidad
            libro.save()
            
            mensaje = (
                f"Se agregaron {cantidad} ejemplar(es) al préstamo existente. "
                f"Total en préstamo: {prestamo_existente.cantidad} ejemplar(es). "
                f"Stock restante: {libro.cantidad}."
            )
            prestamo = prestamo_existente
        else:
            # Crear nuevo préstamo
            prestamo = PrestamoLibro.objects.create(
                libro=libro,
                usuario=usuario,
                cantidad=cantidad,
                fecha_devolucion=fecha_devolucion,
                prestado_por=prestado_por,
                observaciones=observaciones or ""
            )
            
            # Restar del inventario
            libro.cantidad -= cantidad
            libro.save()
            
            mensaje = (
                f"Préstamo creado exitosamente. {cantidad} ejemplar(es) prestado(s). "
                f"Stock restante: {libro.cantidad}."
            )

        return CrearPrestamo(prestamo=prestamo, mensaje=mensaje)


class DevolverLibro(graphene.Mutation):
    """Devuelve un libro (total o parcialmente) y actualiza el inventario"""
    prestamo = graphene.Field(PrestamoLibroType)
    mensaje = graphene.String()

    class Arguments:
        prestamo_id = graphene.ID(required=True)
        cantidad = graphene.Int(required=False)

    @login_required
    @transaction.atomic
    def mutate(self, info, prestamo_id, cantidad=None):
        try:
            prestamo = PrestamoLibro.objects.select_related('libro').select_for_update().get(pk=prestamo_id)
        except PrestamoLibro.DoesNotExist:
            raise GraphQLError("El préstamo no existe.")

        if prestamo.devuelto:
            raise GraphQLError("El préstamo ya fue devuelto completamente.")

        # Si no se especifica cantidad, se devuelve todo
        cantidad_a_devolver = cantidad if cantidad is not None else prestamo.cantidad

        # Validaciones
        if cantidad_a_devolver <= 0:
            raise GraphQLError("La cantidad a devolver debe ser mayor que 0.")

        if cantidad_a_devolver > prestamo.cantidad:
            raise GraphQLError(
                f"No puedes devolver más de lo prestado. "
                f"Cantidad prestada: {prestamo.cantidad}, intentas devolver: {cantidad_a_devolver}."
            )

        # Obtener el libro con lock
        libro = Libro.objects.select_for_update().get(pk=prestamo.libro.pk)
        
        # Sumar al inventario
        libro.cantidad += cantidad_a_devolver
        libro.save()

        # Actualizar el préstamo
        if cantidad_a_devolver == prestamo.cantidad:
            # Devolución completa
            prestamo.devuelto = True
            prestamo.recibido_por = info.context.user
            prestamo.save()
            
            mensaje = (
                f"El libro '{libro.titulo}' fue devuelto completamente. "
                f"Se devolvieron {cantidad_a_devolver} ejemplar(es). "
                f"Stock actual: {libro.cantidad}."
            )
        else:
            # Devolución parcial
            prestamo.cantidad -= cantidad_a_devolver
            prestamo.recibido_por = info.context.user
            
            # Agregar observación
            observacion_devolucion = (
                f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] "
                f"Devolución parcial de {cantidad_a_devolver} ejemplar(es). "
                f"Quedan {prestamo.cantidad} en préstamo."
            )
            prestamo.observaciones = (prestamo.observaciones or "") + observacion_devolucion
            prestamo.save()
            
            mensaje = (
                f"Devolución parcial registrada. Se devolvieron {cantidad_a_devolver} ejemplar(es). "
                f"Aún quedan {prestamo.cantidad} ejemplar(es) en préstamo. "
                f"Stock actual del libro: {libro.cantidad}."
            )

        return DevolverLibro(prestamo=prestamo, mensaje=mensaje)


class EliminarTodosLosPrestamos(graphene.Mutation):
    """Elimina todos los préstamos del sistema"""
    ok = graphene.Boolean()
    total_eliminados = graphene.Int()

    @login_required
    def mutate(self, info):
        user = info.context.user

        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("No tienes permisos para eliminar todos los préstamos.")

        total = PrestamoLibro.objects.count()
        if total == 0:
            raise GraphQLError("No hay préstamos para eliminar.")

        PrestamoLibro.objects.all().delete()
        return EliminarTodosLosPrestamos(ok=True, total_eliminados=total)


# =====================================================
#  REGISTRO DE MUTACIONES EN EL SCHEMA
# =====================================================
class Mutation(graphene.ObjectType):
    agregar_libro = AgregarLibro.Field()
    sumar_cantidad_libro = SumarCantidadLibro.Field()
    eliminar_cantidad_libro = EliminarCantidadLibro.Field()
    actualizar_libro = ActualizarLibro.Field()
    crear_prestamo = CrearPrestamo.Field()
    devolver_libro = DevolverLibro.Field()
    eliminar_todos_los_prestamos = EliminarTodosLosPrestamos.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)