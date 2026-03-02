import graphene


class PaginationType(graphene.ObjectType):
    items = graphene.List(graphene.JSONString)
    total_items = graphene.Int()
    total_pages = graphene.Int()
    per_page = graphene.Int()
    current_page = graphene.Int()
    next_page = graphene.Int()
    previous_page = graphene.Int()
    total_unread_items = graphene.Int()
    total_read_items = graphene.Int()
