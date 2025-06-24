from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="finml_trader_pipeline",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None, # This means trigger it manually
    tags=["finml", "mlops"],
) as dag:
    
    # This task runs our data ingestion script
    # It executes the script using the python interpreter inside the container
    ingest_data = BashOperator(
        task_id="ingest_data",
        bash_command="python /opt/airflow/scripts/data_ingestion.py",
    )

    # This task runs our model training script
    train_model = BashOperator(
        task_id="train_model",
        bash_command="python /opt/airflow/scripts/train_baseline_model.py",
    )

    # This defines the dependency: train_model will only run after ingest_data succeeds
    ingest_data >> train_model