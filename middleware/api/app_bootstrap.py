from typing import ClassVar

from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory as AdapterObjectsFactory
from middleware.adapters.daos.objects_factory import ObjectsFactory as DaoObjectsFactory
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.objects_factory import ObjectsFactory as FacadeObjectsFactory


@log_methods
class AppBootstrap:
    _instance: ClassVar["AppBootstrap | None"] = None

    def __init__(self) -> None:
        self.name = "AppBootstrap"
        self.description = "Initializes dao, adapter, and facade objects"
        self.initialized = False

    @staticmethod
    def get_instance() -> "AppBootstrap":
        if AppBootstrap._instance is None:
            AppBootstrap._instance = AppBootstrap()
        return AppBootstrap._instance

    def init(self) -> None:
        if self.initialized:
            return
        logger = get_logger(__name__)
        DaoObjectsFactory.get_instance().init()
        try:
            AdapterObjectsFactory.get_instance().init()
        except Exception:
            logger.exception(
                "Azure adapter bootstrap failed; continuing application startup",
            )
        FacadeObjectsFactory.get_instance().init()
        self.initialized = True
