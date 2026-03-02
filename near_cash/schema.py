from graphene import Schema, ObjectType, JSONString
import graphene
from graphql_jwt.decorators import login_required
from apps.auths.schema.mutations.auth_mutations import Mutation as AuthMutation
from apps.auths.schema.queries.auth_queries import Query as AuthQuery
from apps.auths.schema.mutations.user_mutations import Mutation as UserMutation
from apps.wallet.schema.mutations.wallet import Mutation as WalletMutation
from apps.wallet.schema.queries.wallet import Query as WalletQuery
from apps.core.schema.mutations.business_mutations import Mutation as BusinessMutation
from apps.core.schema.mutations.client_mutations import Mutation as ClientMutation
from apps.core.schema.queries.business_queries import Query as BusinessQuery
from apps.notification.schema.queries.notification_queries import Query as NotificationQuery
from apps.notification.schema.mutations.notifications import Mutation as NotificationMutation

from utils.helpers.types import PaginationType

class RootQuery(
    AuthQuery,
    WalletQuery,
    BusinessQuery,
    NotificationQuery,
    ObjectType
):
    """
    Root query for the GraphQL schema.
    """
    pagination = graphene.Field(PaginationType)

    def resolve_pagination(self, info):
        return info.context.pagination


class RootMutation(
    AuthMutation,
    UserMutation,
    WalletMutation,
    BusinessMutation,
    ClientMutation,
    NotificationMutation,
    ObjectType
):
    """
    Root mutation for the GraphQL schema.
    """
    pass

schema = Schema(query=RootQuery, mutation=RootMutation)
