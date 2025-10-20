import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required
from django.contrib.auth import get_user_model
from graphql import GraphQLError

User = get_user_model()

# =======================================
# 🎯 TIPOS DE GRAPHQL (Types)
# =======================================
class UserType(DjangoObjectType):
    """Tipo GraphQL para el modelo User"""

    nombre_completo = graphene.String()
    puede_gestionar_bienes = graphene.Boolean()
    puede_gestionar_biblioteca = graphene.Boolean()
    es_administrador = graphene.Boolean()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'dni', 'telefono',
            'rol', 'es_docente', 'grado', 'seccion', 'turno', 'nivel',
            'fecha_registro', 'ultima_actualizacion'
        )

    def resolve_nombre_completo(self, info):
        return self.get_nombre_completo()

    def resolve_puede_gestionar_bienes(self, info):
        return self.puede_gestionar_bienes()

    def resolve_puede_gestionar_biblioteca(self, info):
        return self.puede_gestionar_biblioteca()

    def resolve_es_administrador(self, info):
        return self.es_administrador()


# =======================================
# 📚 QUERIES (Consultas)
# =======================================
class Query(graphene.ObjectType):
    """Consultas GraphQL para usuarios"""

    # Usuario actual logueado
    me = graphene.Field(UserType)  
     #Obtener un usuario por ID
    usuario = graphene.Field(UserType, id=graphene.Int(required=True))
    #Listar todo los usuarios (solo admin)
    todos_usuarios = graphene.List(UserType)
    #Filtrar por rol especifico
    usuarios_por_rol = graphene.List(UserType, rol=graphene.String(required=True))
    #Obtener todos los docentes
    docentes = graphene.List(UserType)

    @login_required
    def resolve_me(self, info):
        """Retorna el usuario actual"""
        return info.context.user

    @login_required
    def resolve_usuario(self, info, id):
        """Obtener un usuario específico"""
        current_user = info.context.user
        if not current_user.es_administrador() and current_user.id != id:
            raise GraphQLError("No tienes permiso para ver este usuario.")
        try:
            return User.objects.get(pk=id)
        except User.DoesNotExist:
            raise GraphQLError("Usuario no encontrado.")

    @login_required
    def resolve_todos_usuarios(self, info):
        """Lista de todos los usuarios (solo admin)"""
        current_user = info.context.user
        if not current_user.es_administrador():
            raise GraphQLError("Solo los administradores pueden ver todos los usuarios.")
        return User.objects.all()

    @login_required
    def resolve_usuarios_por_rol(self, info, rol):
        """Buscar usuarios por rol"""
        current_user = info.context.user
        if not current_user.es_administrador():
            raise GraphQLError("No tienes permiso para esta operación.")
        return User.objects.filter(rol=rol)

    @login_required
    def resolve_docentes(self, info):
        """Obtener todos los docentes"""
        return User.objects.filter(es_docente=True)


# =======================================
# 🔧 MUTACIONES (Modificaciones)
# =======================================

# ---- Registrar nuevo usuario ----
class RegistrarUsuario(graphene.Mutation):
    """Registrar un nuevo usuario general o docente."""
    user = graphene.Field(UserType)
    mensaje = graphene.String()

    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
        email = graphene.String()
        first_name = graphene.String(required=True)
        last_name = graphene.String(required=True)
        dni = graphene.String()
        telefono = graphene.String()
        es_docente = graphene.Boolean(required=False, default_value=False)
        grado = graphene.String()
        seccion = graphene.String()
        turno = graphene.String()
        nivel = graphene.String()

    def mutate(self, info, username, password, first_name, last_name,
               email=None, dni=None, telefono=None,
               es_docente=False, grado=None, seccion=None,
               turno=None, nivel=None):
        
        # 🚨 VALIDACIÓN CRÍTICA: Asegurar que la contraseña no esté vacía 🚨
        if not password or password.strip() == "":
            raise GraphQLError("La contraseña es obligatoria y no puede estar vacía.")

        # Validar si ya existe el usuario
        if User.objects.filter(username=username).exists():
            raise GraphQLError("Ya existe un usuario con ese nombre de usuario.")

        # Crear el usuario
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            dni=dni,
            telefono=telefono,
            es_docente=es_docente,
        )

        # Si el usuario es docente, guardar también los campos docentes
        if es_docente:
            user.grado = grado 
            user.seccion = seccion 
            user.turno = turno 
            user.nivel = nivel 
        else:
            # Si NO es docente, dejar vacíos esos campos
            user.grado = None
            user.seccion = None
            user.turno = None
            user.nivel = None

        user.save()

        return RegistrarUsuario(user=user, mensaje="Usuario registrado correctamente.")


# ---- Actualizar usuario ----
class ActualizarUsuario(graphene.Mutation):
    """Actualizar datos de un usuario"""
    user = graphene.Field(UserType)
    mensaje = graphene.String()

    class Arguments:
        id = graphene.Int(required=True)
        first_name = graphene.String()
        last_name = graphene.String()
        email = graphene.String()
        telefono = graphene.String()
        dni = graphene.String()
        grado = graphene.String()
        seccion = graphene.String()
        turno = graphene.String()
        nivel = graphene.String()
        es_docente = graphene.Boolean()
        rol = graphene.String()

    @login_required
    def mutate(self, info, id, **kwargs):
        current_user = info.context.user
        try:
            user_to_update = User.objects.get(pk=id)
        except User.DoesNotExist:
            raise GraphQLError("Usuario no encontrado.")

        # Solo admin puede editar a otros o cambiar roles
        if not current_user.es_administrador() and current_user.id != id:
            raise GraphQLError("No tienes permiso para actualizar este usuario.")
        if "rol" in kwargs and not current_user.es_administrador():
            raise GraphQLError("Solo los administradores pueden cambiar roles.")

        for field, value in kwargs.items():
            if value is not None:
                setattr(user_to_update, field, value)
        user_to_update.save()

        return ActualizarUsuario(user=user_to_update, mensaje="Usuario actualizado exitosamente.")


# ---- Cambiar contraseña ----
class CambiarPassword(graphene.Mutation):
    """Cambiar contraseña del usuario actual"""
    mensaje = graphene.String()

    class Arguments:
        password_actual = graphene.String(required=True)
        password_nuevo = graphene.String(required=True)

    @login_required
    def mutate(self, info, password_actual, password_nuevo):
        current_user = info.context.user
        if not current_user.check_password(password_actual):
            raise GraphQLError("La contraseña actual es incorrecta.")
        current_user.set_password(password_nuevo)
        current_user.save()
        return CambiarPassword(mensaje="Contraseña cambiada exitosamente.")


# ---- Eliminar usuario ----
class EliminarUsuario(graphene.Mutation):
    """Eliminar (borrar permanentemente) un usuario"""
    mensaje = graphene.String()

    class Arguments:
        id = graphene.Int(required=True)

    @login_required
    def mutate(self, info, id):
        current_user = info.context.user
        if not current_user.es_administrador():
            raise GraphQLError("Solo los administradores pueden eliminar usuarios.")

        try:
            user_to_delete = User.objects.get(pk=id)
        except User.DoesNotExist:
            raise GraphQLError("Usuario no encontrado.")

        if user_to_delete.id == current_user.id:
            raise GraphQLError("No puedes eliminarte a ti mismo.")

        user_to_delete.delete()
        return EliminarUsuario(mensaje="Usuario eliminado exitosamente.")


# =======================================
# 🧩 REGISTRO DE MUTACIONES
# =======================================
class Mutation(graphene.ObjectType):
    registrar_usuario = RegistrarUsuario.Field()
    actualizar_usuario = ActualizarUsuario.Field()
    cambiar_password = CambiarPassword.Field()
    eliminar_usuario = EliminarUsuario.Field()
