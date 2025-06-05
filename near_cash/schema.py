from graphene import Schema, ObjectType
from apps.auths.schema.mutations.auth_mutations import Mutation as AuthMutation
from apps.auths.schema.queries.auth_queries import Query as AuthQuery

class RootQuery(
    AuthQuery,
    ObjectType
):
    """
    Root query for the GraphQL schema.
    """
    pass

class RootMutation(
    AuthMutation,
    ObjectType
):
    """
    Root mutation for the GraphQL schema.
    """
    pass

schema = Schema(query=RootQuery, mutation=RootMutation)
