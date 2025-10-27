import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from django.utils import timezone
from graphql_jwt.decorators import login_required  
from .models import Libro, PrestamoLibro


# =====================================================
#  TIPOS (Representan tus modelos en GraphQL)
# =====================================================
class LibroType(DjangoObjectType):
    """Tipo GraphQL que representa el modelo Libro"""
    class Meta:
        model = Libro
        fields = "__all__"


class PrestamoLibroType(DjangoObjectType):
    """Tipo GraphQL que representa el modelo PrestamoLibro"""
    class Meta:
        model = PrestamoLibro
        fields = "__all__"


# =====================================================
#  QUERIES (Consultas de lectura)
# =====================================================
class Query(graphene.ObjectType):
    # Lista completa de libros registrados
    libros = graphene.List(LibroType)

    # Lista completa de préstamos registrados
    prestamos = graphene.List(PrestamoLibroType)

    # Detalle de un libro específico por su ID
    libro_por_id = graphene.Field(LibroType, id=graphene.Int(required=True))

    # Préstamos de un usuario específico (para uso administrativo)
    prestamos_por_usuario = graphene.List(
        PrestamoLibroType,
        usuario_id=graphene.Int(required=True)
    )

    # Préstamos del usuario autenticado (para uso del usuario final)
    mis_prestamos = graphene.List(PrestamoLibroType)

    # -----------------------------------------------------
    # RESOLVERS (Lógica que ejecuta cada consulta)
    # -----------------------------------------------------
    @login_required
    def resolve_libros(root, info):
        """Devuelve todos los libros de la base de datos"""
        return Libro.objects.all()
    
    @login_required
    def resolve_prestamos(root, info):
        """Devuelve todos los préstamos con sus relaciones"""
        return PrestamoLibro.objects.select_related("libro", "usuario").all()
    
    @login_required
    def resolve_libro_por_id(root, info, id):
        """Busca un libro específico por su ID"""
        try:
            return Libro.objects.get(pk=id)
        except Libro.DoesNotExist:
            raise GraphQLError("Libro no encontrado.")
        
    @login_required
    def resolve_prestamos_por_usuario(root, info, usuario_id):
        """Devuelve todos los préstamos realizados por un usuario específico"""
        return PrestamoLibro.objects.select_related("libro", "usuario").filter(usuario_id=usuario_id)

    @login_required
    def resolve_mis_prestamos(self, info):
        """Devuelve solo los préstamos del usuario autenticado"""
        user = info.context.user
        return PrestamoLibro.objects.select_related("libro").filter(usuario=user)

# =====================================================
#  MUTACIONES PARA LIBROS
# =====================================================
class AgregarLibro(graphene.Mutation):
    """Agrega un nuevo libro al sistema"""
    libro = graphene.Field(LibroType)

    class Arguments:
        titulo = graphene.String(required=True)
        autor = graphene.String(required=True)
        isbn = graphene.String(required=True)
        editorial = graphene.String(required=False)
        cantidad = graphene.Int(required=True)
        numero_paginas = graphene.Int(required=False)

    @login_required
    def mutate(self, info, titulo, autor, isbn, editorial= None, cantidad = 1, numero_paginas=None):
        user = info.context.user

        # Evitar duplicados
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

#--------------------------------------------------------------------

class SumarCantidadLibro(graphene.Mutation):
    """Suma (o resta) cantidad de ejemplares de un libro"""
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

        # Si la cantidad queda negativa, se pone en cero
        if libro.cantidad < 0:
            libro.cantidad = 0

        libro.save()
        return SumarCantidadLibro(libro=libro)


#-------------------------------------------------------------------------

class EliminarCantidadLibro(graphene.Mutation):
    """Resta una cantidad al libro; si llega a 0, se elimina"""
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

        # Validar cantidad positiva
        if cantidad <= 0:
            raise GraphQLError("La cantidad a restar debe ser mayor que 0.")

        # Restar la cantidad
        libro.cantidad -= cantidad

        # Si la cantidad llega a 0 o menos, eliminar el libro
        if libro.cantidad <= 0:
            libro.delete()
            return EliminarCantidadLibro(libro=None, eliminado=True)

        # Si no llega a cero, guardar los cambios
        libro.save()
        return EliminarCantidadLibro(libro=libro, eliminado=False)

#--------------------------------------------------------------------------
class ActualizarLibro(graphene.Mutation):
    """Permite corregir información del libro (título, autor, editorial, etc.)"""
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
#  REGISTRO DE MUTACIONES EN EL SCHEMA
# =====================================================
class Mutation(graphene.ObjectType):
    agregar_libro = AgregarLibro.Field()
    sumar_cantidad_libro = SumarCantidadLibro.Field()
    eliminar_cantidad_libro = EliminarCantidadLibro.Field()
    actualizar_libro = ActualizarLibro.Field()
