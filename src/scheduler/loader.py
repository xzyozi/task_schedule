import logging
from typing import List

import yaml
from apscheduler.schedulers.base import BaseScheduler
from pydantic import ValidationError

from .models import Config, JobConfig

def load_jobs_from_config(scheduler: BaseScheduler, config_path: str):
    """Loads jobs from a YAML file and adds them to the scheduler."""
    logging.info(f"Loading job configurations from {config_path}...")
    try:
        with open(config_path, 'r') as f:
            raw_configs = yaml.safe_load(f)
            if not raw_configs:
                logging.warning(f"Configuration file {config_path} is empty.")
                return

        validated_config = Config.model_validate(raw_configs)
        validated_jobs: List[JobConfig] = validated_config.root

    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        return
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file: {e}")
        return
    except ValidationError as e:
        logging.error(f"Configuration validation error: {e}")
        return

    for job in validated_jobs:
        try:
            trigger_config = job.trigger.dict()
            trigger_type = trigger_config.pop('type')
            
            scheduler.add_job(
                func=job.func,
                trigger=trigger_type,
                args=job.args,
                kwargs=job.kwargs,
                id=job.id,
                replace_existing=job.replace_existing,
                max_instances=job.max_instances,
                coalesce=job.coalesce,
                misfire_grace_time=job.misfire_grace_time,
                **trigger_config,
            )
            logging.info(f"Successfully scheduled job: {job.id}")
        except Exception as e:
            logging.error(f"Failed to schedule job {job.id}: {e}")
