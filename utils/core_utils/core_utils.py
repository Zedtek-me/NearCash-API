from typing import Union, Optional, Type

from django.db import transaction

from apps.core.models import (
    Business, BusinessTransactionPolicy,
    BusinessClientCategory, CategoryClient
)

from apps.auths.models import User

from utils.helpers.exception import CustomException

class CoreUtil:

    @classmethod
    def create_business_transaction_policy(
        cls, business: Business, data: dict
    ) -> Optional[BusinessTransactionPolicy]:
        """creates a transaction policy for business"""
        with transaction.atomic():
            return BusinessTransactionPolicy.objects.create(business=business, **data)

    @classmethod
    def fetch_business_txn_policy(
        cls, business_id: Union[int, str], filter_data: dict,
        only_one: Optional[bool] = True
    ) -> Union[BusinessTransactionPolicy, None]:
        """returns a txn policy for this business that matches filter data"""
        policies = BusinessTransactionPolicy.objects.filter(
                business__id=business_id, **filter_data
            )
        if only_one:
            return policies.first()
        return policies

    @classmethod
    def create_business_txn_policy(
        cls, business, policy_data: dict
    ) -> Optional[BusinessTransactionPolicy]:
        """creates business financial txn policy"""
        return BusinessTransactionPolicy.objects.create(
            business=business, **policy_data
        )

    @classmethod
    def create_business_client_category(
        cls, business: Business, category_data: dict
    ) -> BusinessClientCategory:
        """
        creates a category into which businesses can categorize their clients

        Args:
            business (_Business_): _business initiating_
            category_data (_dict_): _category data_

        Returns:
            BusinessClientCategory: _model category object_
        """
        policy_id = category_data.pop("transaction_policy_id", None)
        policy = BusinessTransactionPolicy.objects.filter(id=policy_id).first()
        if policy_id and not policy:
            raise CustomException("invalid transaction policy id provided!")
        category_data["txn_policy"] = policy
        return BusinessClientCategory.objects.create(
            business=business, **category_data
        )

    @classmethod
    def add_client_to_category(
        cls, user: User, data: Union[
            Type["AddClientToCategoryInputType"], dict
        ]
    ) -> CategoryClient:
        """adds a client to a business category"""
        category_id = data.get("category_id")
        client_ids = data.get("client_ids")
        clients = User.objects.filter(id__in=client_ids)
        db_category_clients = []
        category = BusinessClientCategory.objects.filter(
            id=category_id, business__owner=user
        ).first()
        if not category:
            raise CustomException(
                message="The provided category does not exist in this user business!"
            )
        if not clients or clients.count() < 1:
            raise CustomException(
                message=f"Invalid client ID: {client_id}"
            )
        for client_user in clients:
            db_category_clients.append(
                CategoryClient.objects.create(
                    category=category,
                    client=client_user
                )
            )
        return db_category_clients
