from graphene import Schema, ObjectType, JSONString
from apps.auths.schema.mutations.auth_mutations import Mutation as AuthMutation
from apps.auths.schema.queries.auth_queries import Query as AuthQuery
from apps.auths.schema.mutations.user_mutations import Mutation as UserMutation
from apps.wallet.schema.mutations.wallet import Mutation as WalletMutation
from apps.wallet.schema.queries.wallet import Query as WalletQuery
from apps.core.schema.mutations.business_mutations import Mutation as BusinessMutation
from apps.core.schema.mutations.client_mutations import Mutation as ClientMutation
from apps.core.schema.queries.business_queries import Query as BusinessQuery

class RootQuery(
    AuthQuery,
    WalletQuery,
    BusinessQuery,
    ObjectType
):
    """
    Root query for the GraphQL schema.
    """
    pagination = JSONString()

    def resolve_pagination(self, info):
        return info.context.pagination


class RootMutation(
    AuthMutation,
    UserMutation,
    WalletMutation,
    BusinessMutation,
    ClientMutation,
    ObjectType
):
    """
    Root mutation for the GraphQL schema.
    """
    pass

schema = Schema(query=RootQuery, mutation=RootMutation)
