import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from django.utils import timezone
from graphql_jwt.decorators import login_required  # ✅ Import necesario
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

    def resolve_libros(root, info):
        """Devuelve todos los libros de la base de datos"""
        return Libro.objects.all()

    def resolve_prestamos(root, info):
        """Devuelve todos los préstamos con sus relaciones"""
        return PrestamoLibro.objects.select_related("libro", "usuario").all()

    def resolve_libro_por_id(root, info, id):
        """Busca un libro específico por su ID"""
        try:
            return Libro.objects.get(pk=id)
        except Libro.DoesNotExist:
            raise GraphQLError("Libro no encontrado.")

    def resolve_prestamos_por_usuario(root, info, usuario_id):
        """Devuelve todos los préstamos realizados por un usuario específico"""
        return PrestamoLibro.objects.select_related("libro", "usuario").filter(usuario_id=usuario_id)

    @login_required
    def resolve_mis_prestamos(self, info):
        """Devuelve solo los préstamos del usuario autenticado"""
        user = info.context.user
        return PrestamoLibro.objects.select_related("libro").filter(usuario=user)
