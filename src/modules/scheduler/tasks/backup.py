from util import logger_util
from ..task_utils import task

logger = logger_util.get_logger(__name__)

@task(name="Backup Data", description="A sample task for performing data backup.")
def backup_data():
    logger.info("Performing data backup...")
    print("Performing data backup...")
    pass
