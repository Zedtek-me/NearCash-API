from typing import List, Dict, Union, Optional

class KwargUtil:

    @classmethod
    def cherry_pick_data(
        cls, data: dict, filter_keys: Optional[List[str]] = None
    ) -> Union[List, Dict, tuple]:
        """unpacks the values of a dict into a list or tuple"""
        return [data.get(key) for key in filter_keys] if filter_keys else list(data.values())
