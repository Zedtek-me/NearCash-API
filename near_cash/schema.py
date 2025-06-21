from graphene import Schema, ObjectType
from apps.auths.schema.mutations.auth_mutations import Mutation as AuthMutation
from apps.auths.schema.queries.auth_queries import Query as AuthQuery
from apps.auths.schema.mutations.user_mutations import Mutation as UserMutation
from apps.wallet.schema.mutations.wallet import Mutation as WalletMutation
from apps.wallet.schema.queries.wallet import Query as WalletQuery

class RootQuery(
    AuthQuery,
    WalletQuery,
    ObjectType
):
    """
    Root query for the GraphQL schema.
    """
    pass

class RootMutation(
    AuthMutation,
    UserMutation,
    WalletMutation,
    ObjectType
):
    """
    Root mutation for the GraphQL schema.
    """
    pass

schema = Schema(query=RootQuery, mutation=RootMutation)
