from middleware.common.entity.abstract_base_entity import AbstractBaseEntity
from middleware.common.utils.logger_util import log_methods


@log_methods
class PersistCtx[EntityT: AbstractBaseEntity]:
    entity: EntityT

    def __init__(self, entity: EntityT) -> None:
        self.entity = entity

    def get_entity(self) -> EntityT:
        return self.entity
