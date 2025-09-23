from sqlalchemy.orm import Session
from core.crud import CRUDBase
from . import models, schemas

class JobDefinitionCRUD(CRUDBase[models.JobDefinition, schemas.JobConfig, schemas.JobConfig]):
    def create_from_config(self, db: Session, *, job_in: schemas.JobConfig) -> models.JobDefinition:
        """
        Creates a JobDefinition in the database from a JobConfig Pydantic schema.
        """
        trigger_dict = job_in.trigger.dict()
        trigger_type = trigger_dict.pop('type')
        
        db_obj = self.model(
            id=job_in.id,
            func=job_in.func,
            description=job_in.description,
            is_enabled=job_in.is_enabled,
            trigger_type=trigger_type,
            trigger_config=trigger_dict,
            args=job_in.args,
            kwargs=job_in.kwargs,
            max_instances=job_in.max_instances,
            coalesce=job_in.coalesce,
            misfire_grace_time=job_in.misfire_grace_time,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_from_config(self, db: Session, *, db_obj: models.JobDefinition, job_in: schemas.JobConfig) -> models.JobDefinition:
        """
        Updates a JobDefinition in the database from a JobConfig Pydantic schema.
        """
        db_obj.func = job_in.func
        db_obj.description = job_in.description
        db_obj.is_enabled = job_in.is_enabled
        
        trigger_dict = job_in.trigger.dict()
        db_obj.trigger_type = trigger_dict.pop('type')
        db_obj.trigger_config = trigger_dict

        db_obj.args = job_in.args
        db_obj.kwargs = job_in.kwargs
        db_obj.max_instances = job_in.max_instances
        db_obj.coalesce = job_in.coalesce
        db_obj.misfire_grace_time = job_in.misfire_grace_time
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

job_definition_service = JobDefinitionCRUD(models.JobDefinition)
