import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from django.utils import timezone
from django.db.models import Q
from .models import Asset, AssetAssignment
from users.schema import UserType
from graphql_jwt.decorators import login_required


class AssetType(DjangoObjectType):
    """Tipo GraphQL para el modelo Asset (Bien)"""
    esta_disponible = graphene.Boolean()
    
    class Meta:
        model = Asset
        fields = "__all__"
    
    def resolve_esta_disponible(self, info):
        """Resolver el método esta_disponible del modelo"""
        return self.esta_disponible()


class AssetAssignmentType(DjangoObjectType):
    """Tipo GraphQL para el modelo AssetAssignment (Asignación de Bien)"""
    class Meta:
        model = AssetAssignment
        fields = "__all__"


# =======================================
# QUERIES (Consultas)
# =======================================

class Query(graphene.ObjectType):
    """Consultas GraphQL para bienes y asignaciones"""
    
    # Obtener un bien específico por su ID
    bien = graphene.Field(AssetType, id=graphene.Int(required=True))
    # Obtener una asignación específica por su ID
    asignacion = graphene.Field(AssetAssignmentType, id=graphene.Int(required=True))


    # Queries de listados de bienes
    todos_bienes = graphene.List(
        AssetType,
        nombre=graphene.String(),
        tipo=graphene.String(),
        estado=graphene.String(),
        buscar=graphene.String()
    )
    # Obtener todos los bienes que están disponibles
    bienes_disponibles = graphene.List(AssetType)
    
    # Obtener todos los bienes filtrados por tipo (MOVIL, INMOVIL)
    bienes_por_tipo = graphene.List(AssetType, tipo=graphene.String(required=True))

    # Obtener todos los bienes filtrados por estado (DISPONIBLE , EN_USIO, DANADO, BAJA)
    bienes_por_estado = graphene.List(AssetType, estado=graphene.String(required=True))
    

   # ------------------------------------
    #Devuelve los bienes asignados al usuario que está actualmente autenticado
    mis_bienes = graphene.List(AssetType)
   # Obtener los bienes asignados a un usuario específico mediante su ID
    bienes_usuario = graphene.List(AssetType, usuario_id=graphene.Int(required=True))
    
    # Queries de asignaciones
    #Devuelve todas las asignaciones y permite filtrar opcionalmente por tipo o estado.
    todas_asignaciones = graphene.List(
        AssetAssignmentType,
        tipo_asignacion=graphene.String(),
        estado=graphene.String()
    )
    #Devuelve solo las asignaciones actualmente activas (sin devolución registrada).
    asignaciones_activas = graphene.List(AssetAssignmentType)
    #Devuelve las asignaciones según el tipo (PRESTAMO o ASIGNACION)
    asignaciones_por_tipo = graphene.List(
        AssetAssignmentType, 
        tipo_asignacion=graphene.String(required=True)
    )
    #Devuelve las asignaciones según el estado (ACTIVA, DEVUELTO, TRANSFERIDO)
    asignaciones_por_estado = graphene.List(
        AssetAssignmentType,
        estado=graphene.String(required=True)
    )

    #---------------------------------------------------

    # Queries de historial
    # Obtener el historial completo de asignaciones y préstamos de un bien específico
    historial_bien = graphene.List(AssetAssignmentType, bien_id=graphene.Int(required=True))
    # Obtener el historial de asignaciones y préstamos realizados a un usuario específico

    historial_usuario = graphene.List(AssetAssignmentType, usuario_id=graphene.Int(required=True))
    # Obtener el historial de asignaciones del usuario autenticado (según su sesión o token)

    mis_asignaciones = graphene.List(AssetAssignmentType)

    # ===================================
    # RESOLVERS - QUERIES INDIVIDUALES
    # ===================================
    
    @login_required
    def resolve_bien(self, info, id):
        """Obtener un bien específico por ID"""
        try:
            return Asset.objects.get(pk=id)
        except Asset.DoesNotExist:
            raise GraphQLError('Bien no encontrado')
    
    @login_required
    def resolve_asignacion(self, info, id):
        """Obtener una asignación específica por ID"""
        try:
            return AssetAssignment.objects.get(pk=id)
        except AssetAssignment.DoesNotExist:
            raise GraphQLError('Asignación no encontrada')

    # ===================================
    # RESOLVERS - LISTADOS DE BIENES
    # ===================================
    
    @login_required
    def resolve_todos_bienes(self, info, nombre=None, tipo=None, estado=None, buscar=None):
        """
        Obtener todos los bienes con filtros opcionales
        - nombre: Filtro por nombre exacto
        - tipo: Filtro por tipo (MOVIL, INMOVIL)
        - estado: Filtro por estado (DISPONIBLE, EN_USO, DANADO, BAJA)
        - buscar: Búsqueda general por nombre, descripción o código
        """
        queryset = Asset.objects.all()
        
        if nombre:
            queryset = queryset.filter(nombre__icontains=nombre)
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar) |
                Q(descripcion__icontains=buscar) |
                Q(codigo_inventario__icontains=buscar) |
                Q(ubicacion__icontains=buscar)
            )
        
        return queryset
    
    @login_required
    def resolve_bienes_disponibles(self, info):
        """Obtener solo los bienes disponibles para asignar"""
        return Asset.objects.filter(
            estado='DISPONIBLE',
            responsable_actual__isnull=True,
            cantidad__gt=0
        )
    
    @login_required
    def resolve_bienes_por_tipo(self, info, tipo):
        """
        Obtener bienes filtrados por tipo
        - tipo: MOVIL o INMOVIL
        """
        if tipo not in ['MOVIL', 'INMOVIL']:
            raise GraphQLError('Tipo inválido. Debe ser MOVIL o INMOVIL')
        
        return Asset.objects.filter(tipo=tipo)
    
    @login_required
    def resolve_bienes_por_estado(self, info, estado):
        """
        Obtener bienes filtrados por estado
        - estado: DISPONIBLE, EN_USO, DANADO, BAJA
        """
        estados_validos = ['DISPONIBLE', 'EN_USO', 'DANADO', 'BAJA']
        if estado not in estados_validos:
            raise GraphQLError(f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}')
        
        return Asset.objects.filter(estado=estado)

    # ===================================
    # RESOLVERS - BIENES POR USUARIO
    # ===================================
    
    @login_required
    def resolve_mis_bienes(self, info):
        """Obtener los bienes asignados al usuario autenticado"""
        user = info.context.user
        return Asset.objects.filter(responsable_actual=user)
    
    @login_required
    def resolve_bienes_usuario(self, info, usuario_id):
        """Obtener los bienes asignados a un usuario específico"""
        return Asset.objects.filter(responsable_actual_id=usuario_id)

    # ===================================
    # RESOLVERS - LISTADOS DE ASIGNACIONES
    # ===================================
    
    @login_required
    def resolve_todas_asignaciones(self, info, tipo_asignacion=None, estado=None):
        """
        Obtener todas las asignaciones con filtros opcionales
        - tipo_asignacion: PRESTAMO o ASIGNACION
        - estado: ACTIVA, DEVUELTO, TRANSFERIDO
        """
        queryset = AssetAssignment.objects.select_related('bien', 'usuario', 'asignado_por').all()
        
        if tipo_asignacion:
            if tipo_asignacion not in ['PRESTAMO', 'ASIGNACION']:
                raise GraphQLError('Tipo de asignación inválido. Debe ser PRESTAMO o ASIGNACION')
            queryset = queryset.filter(tipo_asignacion=tipo_asignacion)
        
        if estado:
            estados_validos = ['ACTIVA', 'DEVUELTO', 'TRANSFERIDO']
            if estado not in estados_validos:
                raise GraphQLError(f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}')
            queryset = queryset.filter(estado=estado)
        
        return queryset
    
    @login_required
    def resolve_asignaciones_activas(self, info):
        """Obtener solo las asignaciones activas"""
        return AssetAssignment.objects.filter(estado='ACTIVA').select_related(
            'bien', 'usuario', 'asignado_por'
        )
    
    @login_required
    def resolve_asignaciones_por_tipo(self, info, tipo_asignacion):
        """
        Obtener asignaciones filtradas por tipo
        - tipo_asignacion: PRESTAMO o ASIGNACION
        """
        if tipo_asignacion not in ['PRESTAMO', 'ASIGNACION']:
            raise GraphQLError('Tipo de asignación inválido. Debe ser PRESTAMO o ASIGNACION')
        
        return AssetAssignment.objects.filter(tipo_asignacion=tipo_asignacion).select_related(
            'bien', 'usuario', 'asignado_por'
        )
    
    @login_required
    def resolve_asignaciones_por_estado(self, info, estado):
        """
        Obtener asignaciones filtradas por estado
        - estado: ACTIVA, DEVUELTO, TRANSFERIDO
        """
        estados_validos = ['ACTIVA', 'DEVUELTO', 'TRANSFERIDO']
        if estado not in estados_validos:
            raise GraphQLError(f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}')
        
        return AssetAssignment.objects.filter(estado=estado).select_related(
            'bien', 'usuario', 'asignado_por'
        )

    # ===================================
    # RESOLVERS - HISTORIAL
    # ===================================
    
    @login_required
    def resolve_historial_bien(self, info, bien_id):
        """Obtener el historial completo de asignaciones de un bien específico"""
        try:
            Asset.objects.get(pk=bien_id)
        except Asset.DoesNotExist:
            raise GraphQLError('Bien no encontrado')
        
        return AssetAssignment.objects.filter(bien_id=bien_id).select_related(
            'usuario', 'asignado_por'
        ).order_by('-fecha_asignacion')
    
    @login_required
    def resolve_historial_usuario(self, info, usuario_id):
        """Obtener el historial completo de asignaciones de un usuario específico"""
        return AssetAssignment.objects.filter(usuario_id=usuario_id).select_related(
            'bien', 'asignado_por'
        ).order_by('-fecha_asignacion')
    
    @login_required
    def resolve_mis_asignaciones(self, info):
        """Obtener el historial de asignaciones del usuario autenticado"""
        user = info.context.user
        return AssetAssignment.objects.filter(usuario=user).select_related(
            'bien', 'asignado_por'
        ).order_by('-fecha_asignacion')


# =======================================
# MUTATIONS (Mutaciones)
# =======================================

class Mutation(graphene.ObjectType):
    """Placeholder para las mutaciones - se implementarán después"""
    pass


# =======================================
# SCHEMA
# =======================================

schema = graphene.Schema(query=Query, mutation=Mutation)