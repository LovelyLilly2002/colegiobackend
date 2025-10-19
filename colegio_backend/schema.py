import graphene
import graphql_jwt

# Importar los schemas de cada módulo
import users.schema


class Query(
    users.schema.Query,  
    graphene.ObjectType,
):
    pass


class Mutation(
    users.schema.Mutation,  
    graphene.ObjectType
):
    # Mutaciones de autenticación JWT
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
