from middleware.common.entity.abstract_base_entity import AbstractBaseEntity


class JoinerInfo(AbstractBaseEntity):
    def __init__(self) -> None:
        super().__init__()
        self.first_name: str = ""
        self.middle_name: str = ""
        self.last_name: str = ""
        self.email: str = ""
        self.contact_phone: str = ""
        self.contact_address: str = ""
        self.interviewed_by_employee_ids: list[str] = []
        self.interviewed_by_employee_names: list[str] = []
        self.official_role_name: str = ""
        self.internal_role_name: str = ""
        self.joining_official_role_name: str = ""
        self.salary_accepted_usd: float = 0
        self.joining_date: str = ""


class JoinerPreferences(AbstractBaseEntity):
    def __init__(self) -> None:
        super().__init__()
        self.joiner_info_id: str = ""
        self.resumes: str = ""
        self.personal_interests: str = ""
        self.food_preferences: str = ""
