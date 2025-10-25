import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from django.utils import timezone
from django.db.models import Q
from .models import Asset, AssetAssignment
from users.schema import UserType
from graphql_jwt.decorators import login_required
from django.contrib.auth import get_user_model



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
        buscar=graphene.String() # buscar por nombre, descripción o código
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
# ========================================
# MUTATIONS PARA BIENES (ASSET)
# ========================================

class CrearOActualizarBien(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        tipo = graphene.String(required=True)
        codigo_inventario = graphene.String(required=True)
        descripcion = graphene.String()
        cantidad = graphene.Int()
        ubicacion = graphene.String()

    bien = graphene.Field(AssetType)

    def mutate(self, info, nombre, tipo, codigo_inventario, descripcion=None, cantidad=None, ubicacion=None):
        # Buscar si ya existe un bien con ese código
        bien_existente = Asset.objects.filter(codigo_inventario=codigo_inventario).first()

        if bien_existente:
            # Si existe, actualizamos la cantidad
            cantidad_a_sumar = cantidad if cantidad is not None else 1
            bien_existente.cantidad = (bien_existente.cantidad or 0) + cantidad_a_sumar
            bien_existente.descripcion = descripcion or bien_existente.descripcion
            bien_existente.ubicacion = ubicacion or bien_existente.ubicacion
            bien_existente.save()
            return CrearOActualizarBien(bien=bien_existente)
        else:
            # Si no existe, crear un nuevo bien
            nuevo_bien = Asset.objects.create(
                nombre=nombre,
                tipo=tipo,
                codigo_inventario=codigo_inventario,
                descripcion=descripcion,
                cantidad=cantidad if cantidad is not None else 1,
                ubicacion=ubicacion,
                fecha_adquisicion=timezone.now(),
            )
            return CrearOActualizarBien(bien=nuevo_bien)

class EliminarBien(graphene.Mutation):
    """Eliminar (total o parcialmente) un bien del inventario."""
    class Arguments:
        codigo_inventario = graphene.String(required=True)
        cantidad = graphene.Int()  # opcional: si no se pone, elimina todo el bien

    bien = graphene.Field(AssetType)
    mensaje = graphene.String()

    def mutate(self, info, codigo_inventario, cantidad=None):
        try:
            bien = Asset.objects.get(codigo_inventario=codigo_inventario)
        except Asset.DoesNotExist:
            raise GraphQLError("No existe un bien con ese código de inventario.")

        # Si no se especifica cantidad, se elimina el bien completo
        if cantidad is None:
            bien.delete()
            return EliminarBien(bien=None, mensaje="Bien eliminado completamente.")

        # Si la cantidad a eliminar es mayor o igual, eliminar el bien
        if cantidad >= bien.cantidad:
            bien.delete()
            return EliminarBien(bien=None, mensaje="Se eliminaron todas las unidades del bien.")

        # Si no, solo se resta la cantidad
        bien.cantidad -= cantidad
        bien.save()

        return EliminarBien(bien=bien, mensaje=f"Se eliminaron {cantidad} unidades del bien.")

# ========================================
# MUTATIONS PARA ASIGNACIONES (ASSET ASSIGNMENT)
# ========================================

class CrearAsignacion(graphene.Mutation):
    """Mutación para crear o actualizar la asignación de un bien a un usuario."""

    class Arguments:
        bien_id = graphene.Int(required=True, description="ID del bien a asignar")
        usuario_id = graphene.Int(required=True, description="ID del usuario que recibe el bien")
        tipo_asignacion = graphene.String(required=True, description="Tipo de asignación: PRESTAMO o ASIGNACION")
        cantidad_asignada = graphene.Int(description="Cantidad a asignar (por defecto 1)")
        observaciones = graphene.String(description="Notas o comentarios")
        fecha_devolucion_programada = graphene.Date(description="Fecha programada de devolución (solo para préstamos)")

    success = graphene.Boolean()
    mensaje = graphene.String()
    errors = graphene.List(graphene.String)
    asignacion = graphene.Field(AssetAssignmentType)

    @login_required
    def mutate(
        self, info, bien_id, usuario_id, tipo_asignacion,
        cantidad_asignada=None, fecha_devolucion_programada=None,
        observaciones=None
    ):

        # 1️⃣ Validar cantidad (por defecto 1)
        if not cantidad_asignada or cantidad_asignada <= 0:
            cantidad_asignada = 1

        # 2️⃣ Buscar el bien
        try:
            bien = Asset.objects.get(id=bien_id)
        except Asset.DoesNotExist:
            return CrearAsignacion(success=False, errors=["El bien no existe"])

        # 3️⃣ Buscar usuario
        User = get_user_model()
        try:
            usuario = User.objects.get(id=usuario_id)
        except User.DoesNotExist:
            return CrearAsignacion(success=False, errors=["El usuario no existe"])

        # 4️⃣ Validar tipo de asignación
        tipos_validos = [choice[0] for choice in AssetAssignment.TIPOS_ASIGNACION]
        if tipo_asignacion not in tipos_validos:
            return CrearAsignacion(
                success=False,
                errors=[f"Tipo de asignación inválido. Debe ser uno de: {', '.join(tipos_validos)}"]
            )

        # 5️⃣ Validar disponibilidad
        if bien.cantidad < cantidad_asignada:
            return CrearAsignacion(
                success=False,
                errors=[f"No hay suficiente stock. Disponible: {bien.cantidad} unidades."]
            )

        # 6️⃣ Revisar si ya existe una asignación activa del mismo usuario para este bien
        asignacion_existente = AssetAssignment.objects.filter(
            bien=bien,
            usuario=usuario,
            estado='ACTIVA'
        ).first()

        if asignacion_existente:
            # Si existe, sumar la cantidad y actualizar observaciones/fecha si se pasa
            asignacion_existente.cantidad_asignada += cantidad_asignada
            if observaciones:
                asignacion_existente.observaciones = (asignacion_existente.observaciones or '') + f" | {observaciones}"
            if fecha_devolucion_programada:
                asignacion_existente.fecha_devolucion_programada = fecha_devolucion_programada
            asignacion_existente.save()
            asignacion = asignacion_existente
        else:
            # Si no existe, crear una nueva asignación
            asignacion = AssetAssignment.objects.create(
                bien=bien,
                usuario=usuario,
                tipo_asignacion=tipo_asignacion,
                cantidad_asignada=cantidad_asignada,
                fecha_asignacion=timezone.now(),
                fecha_devolucion_programada=fecha_devolucion_programada,
                observaciones=observaciones,
                estado='ACTIVA'
            )

        # 7️⃣ Reducir stock del bien
        bien.cantidad -= cantidad_asignada
        bien.save()

        return CrearAsignacion(
            success=True,
            mensaje=f"{tipo_asignacion.capitalize()} registrada correctamente.",
            asignacion=asignacion
        )

        # ==================================================

class DevolverBien(graphene.Mutation):
    """Mutación para devolver un bien asignado a un usuario."""

    class Arguments:
        usuario_id = graphene.Int(required=True, description="ID del usuario que devuelve el bien")
        codigo_bien = graphene.String(required=True, description="Código de inventario del bien")
        cantidad = graphene.Int(required=True, description="Cantidad que se devuelve")
        observaciones = graphene.String(description="Notas de la devolución")

    success = graphene.Boolean()
    mensaje = graphene.String()

    @login_required
    def mutate(self, info, usuario_id, codigo_bien, cantidad, observaciones=None):
        # 1️⃣ Buscar el bien
        try:
            bien = Asset.objects.get(codigo_inventario=codigo_bien)
        except Asset.DoesNotExist:
            raise GraphQLError("No existe un bien con ese código.")

        # 2️⃣ Buscar la asignación activa del usuario para ese bien
        asignacion = AssetAssignment.objects.filter(
            bien=bien,
            usuario_id=usuario_id,
            estado='ACTIVA'
        ).first()

        if not asignacion:
            raise GraphQLError("El usuario no tiene asignación activa de ese bien.")

        # 3️⃣ Validar cantidad
        if cantidad <= 0:
            raise GraphQLError("La cantidad a devolver debe ser mayor que cero.")

        if cantidad > asignacion.cantidad_asignada:
            raise GraphQLError(
                f"No se puede devolver más de lo asignado. Asignado: {asignacion.cantidad_asignada}"
            )

        # 4️⃣ Actualizar cantidad y stock
        asignacion.cantidad_asignada -= cantidad
        bien.cantidad += cantidad
        bien.save()

        # 5️⃣ Registrar devolución total o parcial
        asignacion.fecha_devolucion = timezone.now()
        if observaciones:
            asignacion.observaciones_devolucion = observaciones

        if asignacion.cantidad_asignada == 0:
            # Si se devolvió todo, eliminar la asignación
            asignacion.delete()
            mensaje = f"Se devolvieron todas las unidades del bien {bien.nombre}. La asignación se eliminó."
        else:
            asignacion.save()
            mensaje = f"Se devolvieron {cantidad} unidades del bien {bien.nombre}. Quedan {asignacion.cantidad_asignada} asignadas."

        return DevolverBien(
            success=True,
            mensaje=mensaje
        )


    #===========================================================================





# ========================================
# REGISTRO EN EL SCHEMA PRINCIPAL
# ========================================
class Mutation(graphene.ObjectType):
    crear_o_actualizarBien = CrearOActualizarBien.Field()
    eliminar_bien = EliminarBien.Field()
    crear_asignacion = CrearAsignacion.Field()
    devolver_bien = DevolverBien.Field()
    