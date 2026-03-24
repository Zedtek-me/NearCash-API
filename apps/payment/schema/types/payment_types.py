import graphene


class BankAccountInfoType(graphene.ObjectType):
    amount = graphene.Float()
    account_number = graphene.String()
    account_name = graphene.String()
    reference = graphene.String()
    account_bank_name = graphene.String()
    account_type = graphene.String()
    status = graphene.String()
    account_expiration_datetime = graphene.String()
    note = graphene.String()
    customer_id = graphene.String()
    created_datetime = graphene.String()
    meta = graphene.String()
    currency = graphene.String()
    provider = graphene.String()
