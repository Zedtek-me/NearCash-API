from typing import Union, Optional, Type, List
import logging

from django.db import transaction
from django.db.models import QuerySet, Q


from apps.core.models import (
    Business, BusinessTransactionPolicy,
    BusinessClientCategory, BusinessClient
)
from apps.core.schema.types.business_types import CashCollectionModes

from utils.helpers.exception import CustomException

logger = logging.getLogger("nearcash")
logger.setLevel(logging.DEBUG)


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
        cash_collection_mode = policy_data.pop("cash_collection_mode", None)
        if cash_collection_mode and not isinstance(
            cash_collection_mode, str
        ):
            policy_data["cash_collection_mode"] = cash_collection_mode.name
        return BusinessTransactionPolicy.objects.create(
            business=business, **policy_data
        )

    @classmethod
    def update_business_txn_policy(
        cls, user, policy_id: int | str, update_data: dict
    ):
        """updates a business transaction policy"""
        policy = BusinessTransactionPolicy.objects.filter(
            id=policy_id, business__owner=user
        ).first()
        if not policy:
            raise CustomException("Invalid transaction policy ID or access denied!")
        for key, value in update_data.items():
            if hasattr(policy, key) and value is not None:
                if key == "cash_collection_mode" and not isinstance(value, str):
                    value = value.name
                setattr(policy, key, value)
        policy.save()
        return policy


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
        cls, user, data: Union[
            Type["AddClientToCategoryInputType"], dict
        ]
    ) -> List[BusinessClient]:
        """adds a client to a business category"""
        from utils.core_utils.business_utils import BusinessUtil
        from apps.auths.models import User

        category_id = data.get("category_id")
        client_ids = data.get("client_ids")
        business_id = data.get("business_id")
        business = BusinessUtil.get_business({"id": business_id})
        clients = User.objects.filter(id__in=client_ids)
        db_category_clients = []
        category = BusinessClientCategory.objects.filter(
            id=category_id, business__owner=user, business=business
        ).first()
        if not category:
            raise CustomException(
                message="The provided category does not exist in this user business!"
            )
        if not clients or clients.count() < 1:
            raise CustomException(
                message=f"Invalid client IDs: {client_ids}"
            )
        for client_user in clients:
            if existing_client := BusinessClient.objects.filter(
                client=client_user, business=business
            ).first():
                existing_client.category = category
                existing_client.save()
                db_category_clients.append(existing_client)
                continue

            db_category_clients.append(
                BusinessClient.objects.create(
                    category=category,
                    client=client_user,
                    business=business
                )
            )
        return db_category_clients


    @classmethod
    def get_or_create_user_as_business_client(
        cls, client, business: Business, category: Optional[BusinessClientCategory] = None
    ) -> BusinessClient:
        """creates a user as a client for the given business"""
        if existing_client := BusinessClient.objects.filter(
            client=client, business=business
        ).first():
            return existing_client
        return BusinessClient.objects.create(
            client=client, category=category,
            business=business
        )


    @classmethod
    def get_business_clients(
        cls, user, data: dict
    ) -> BusinessClient:
        """
        returns clients that have patronized a business.
        """
        from apps.wallet.models import Transaction
        from utils.wallet_utils.transactions import TransactionUtil
        from utils.core_utils.business_utils import BusinessUtil

        business_id = data.get("business_id")
        category_id = data.get("category_id")
        business_filter = {"id": business_id}
        if not business_id:
            client_ids = user.vendor_transactions.values_list("client_id", flat=True)
            return BusinessClient.objects.filter(client__id__in=client_ids).order_by("client_id", "id")\
                .distinct("client_id")
        business = BusinessUtil.get_business(business_filter)
        client_ids = business.transactions.values_list("client_id", flat=True)
        clients = BusinessClient.objects.filter(client__id__in=client_ids).order_by("client_id", "id")\
            .distinct("client_id")
        if category_id:
            clients = clients.filter(category__id=category_id)
        return clients


    @classmethod
    def get_business_client_categories(
        cls, user, data: dict
    ) -> QuerySet:
        """
        returns a list of categories created so far
        in the current business
        """
        from utils.core_utils.business_utils import BusinessUtil

        business_id = data.get("business_id")
        search = data.get("search")
        _id = data.get("id")
        business_filter = {"id": business_id}
        business = BusinessUtil.get_business(business_filter)
        if not business or business.owner != user:
            raise CustomException(
                "invalid business id provided for current user!"
            )
        kwarg_filter = {}
        search_filter = Q()
        if _id:
            kwarg_filter["id"] = _id
        if search:
            search_filter = Q(name__icontains=search) | Q(description__icontains=search)
        categories = BusinessClientCategory.objects.filter(
            search_filter, business=business,
            **kwarg_filter
        )
        return categories
