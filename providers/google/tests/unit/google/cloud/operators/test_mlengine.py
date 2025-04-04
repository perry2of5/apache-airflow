# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

import copy
from unittest import mock
from unittest.mock import ANY, MagicMock, patch

import httplib2
import pytest
from googleapiclient.errors import HttpError

from airflow.exceptions import AirflowException, AirflowProviderDeprecationWarning, TaskDeferred
from airflow.models.dag import DAG
from airflow.models.dagrun import DagRun
from airflow.models.taskinstance import TaskInstance
from airflow.providers.google.cloud.operators.mlengine import (  # AIPlatformConsoleLink,
    MLEngineCreateModelOperator,
    MLEngineCreateVersionOperator,
    MLEngineDeleteModelOperator,
    MLEngineDeleteVersionOperator,
    MLEngineGetModelOperator,
    MLEngineListVersionsOperator,
    MLEngineManageModelOperator,
    MLEngineManageVersionOperator,
    MLEngineSetDefaultVersionOperator,
    MLEngineStartBatchPredictionJobOperator,
    MLEngineStartTrainingJobOperator,
    MLEngineTrainingCancelJobOperator,
)
from airflow.providers.google.cloud.triggers.mlengine import MLEngineStartTrainingJobTrigger
from airflow.utils import timezone
from airflow.utils.timezone import datetime
from airflow.utils.types import DagRunType

DEFAULT_DATE = timezone.datetime(2017, 6, 6)

TEST_DAG_ID = "test-mlengine-operators"
TEST_PROJECT_ID = "test-project-id"
TEST_MODEL_NAME = "test-model-name"
TEST_VERSION_NAME = "test-version"
TEST_GCP_CONN_ID = "test-gcp-conn-id"
TEST_IMPERSONATION_CHAIN = ["ACCOUNT_1", "ACCOUNT_2", "ACCOUNT_3"]
TEST_MODEL = {
    "name": TEST_MODEL_NAME,
}
TEST_VERSION = {
    "name": "v1",
    "deploymentUri": "gs://some-bucket/jobs/test_training/model.pb",
    "runtimeVersion": "1.6",
}
MLENGINE_AI_PATH = "airflow.providers.google.cloud.operators.mlengine.{}"


class TestMLEngineStartBatchPredictionJobOperator:
    INPUT_MISSING_ORIGIN = {
        "dataFormat": "TEXT",
        "inputPaths": ["gs://legal-bucket/fake-input-path/*"],
        "outputPath": "gs://legal-bucket/fake-output-path",
        "region": "us-east1",
    }
    SUCCESS_MESSAGE_MISSING_INPUT = {
        "jobId": "test_prediction",
        "labels": {"some": "labels"},
        "predictionOutput": {
            "outputPath": "gs://fake-output-path",
            "predictionCount": 5000,
            "errorCount": 0,
            "nodeHours": 2.78,
        },
        "state": "SUCCEEDED",
    }
    BATCH_PREDICTION_DEFAULT_ARGS = {
        "project_id": "test-project",
        "job_id": "test_prediction",
        "labels": {"some": "labels"},
        "region": "us-east1",
        "data_format": "TEXT",
        "input_paths": ["gs://legal-bucket-dash-Capital/legal-input-path/*"],
        "output_path": "gs://12_legal_bucket_underscore_number/legal-output-path",
        "task_id": "test-prediction",
    }

    def setup_method(self):
        self.dag = DAG(
            "test_dag",
            default_args={
                "owner": "airflow",
                "start_date": DEFAULT_DATE,
                "end_date": DEFAULT_DATE,
            },
            schedule="@daily",
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_with_model(self, mock_hook):
        input_with_model = self.INPUT_MISSING_ORIGIN.copy()
        input_with_model["modelName"] = "projects/test-project/models/test_model"
        success_message = self.SUCCESS_MESSAGE_MISSING_INPUT.copy()
        success_message["predictionInput"] = input_with_model

        hook_instance = mock_hook.return_value
        hook_instance.get_job.side_effect = HttpError(
            resp=httplib2.Response({"status": 404}), content=b"some bytes"
        )
        hook_instance.create_job.return_value = success_message

        with pytest.warns(AirflowProviderDeprecationWarning):
            prediction_task = MLEngineStartBatchPredictionJobOperator(
                job_id="test_prediction",
                project_id="test-project",
                region=input_with_model["region"],
                data_format=input_with_model["dataFormat"],
                input_paths=input_with_model["inputPaths"],
                output_path=input_with_model["outputPath"],
                model_name=input_with_model["modelName"].split("/")[-1],
                labels={"some": "labels"},
                dag=self.dag,
                task_id="test-prediction",
            )
        prediction_output = prediction_task.execute(None)

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        hook_instance.create_job.assert_called_once_with(
            project_id="test-project",
            job={
                "jobId": "test_prediction",
                "labels": {"some": "labels"},
                "predictionInput": input_with_model,
            },
            use_existing_job_fn=ANY,
        )
        assert success_message["predictionOutput"] == prediction_output

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_with_version(self, mock_hook):
        input_with_version = self.INPUT_MISSING_ORIGIN.copy()
        input_with_version["versionName"] = "projects/test-project/models/test_model/versions/test_version"
        success_message = self.SUCCESS_MESSAGE_MISSING_INPUT.copy()
        success_message["predictionInput"] = input_with_version

        hook_instance = mock_hook.return_value
        hook_instance.get_job.side_effect = HttpError(
            resp=httplib2.Response({"status": 404}), content=b"some bytes"
        )
        hook_instance.create_job.return_value = success_message

        with pytest.warns(AirflowProviderDeprecationWarning):
            prediction_task = MLEngineStartBatchPredictionJobOperator(
                job_id="test_prediction",
                project_id="test-project",
                region=input_with_version["region"],
                data_format=input_with_version["dataFormat"],
                input_paths=input_with_version["inputPaths"],
                output_path=input_with_version["outputPath"],
                model_name=input_with_version["versionName"].split("/")[-3],
                version_name=input_with_version["versionName"].split("/")[-1],
                dag=self.dag,
                task_id="test-prediction",
            )
        prediction_output = prediction_task.execute(None)

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        hook_instance.create_job.assert_called_once_with(
            project_id="test-project",
            job={"jobId": "test_prediction", "predictionInput": input_with_version},
            use_existing_job_fn=ANY,
        )
        assert success_message["predictionOutput"] == prediction_output

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_with_uri(self, mock_hook):
        input_with_uri = self.INPUT_MISSING_ORIGIN.copy()
        input_with_uri["uri"] = "gs://my_bucket/my_models/savedModel"
        success_message = self.SUCCESS_MESSAGE_MISSING_INPUT.copy()
        success_message["predictionInput"] = input_with_uri

        hook_instance = mock_hook.return_value
        hook_instance.get_job.side_effect = HttpError(
            resp=httplib2.Response({"status": 404}), content=b"some bytes"
        )
        hook_instance.create_job.return_value = success_message
        with pytest.warns(AirflowProviderDeprecationWarning):
            prediction_task = MLEngineStartBatchPredictionJobOperator(
                job_id="test_prediction",
                project_id="test-project",
                region=input_with_uri["region"],
                data_format=input_with_uri["dataFormat"],
                input_paths=input_with_uri["inputPaths"],
                output_path=input_with_uri["outputPath"],
                uri=input_with_uri["uri"],
                dag=self.dag,
                task_id="test-prediction",
            )
        prediction_output = prediction_task.execute(None)

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        hook_instance.create_job.assert_called_once_with(
            project_id="test-project",
            job={"jobId": "test_prediction", "predictionInput": input_with_uri},
            use_existing_job_fn=ANY,
        )
        assert success_message["predictionOutput"] == prediction_output

    def test_invalid_model_origin(self):
        # Test that both uri and model is given
        task_args = self.BATCH_PREDICTION_DEFAULT_ARGS.copy()
        task_args["uri"] = "gs://fake-uri/saved_model"
        task_args["model_name"] = "fake_model"
        with pytest.raises(AirflowException) as ctx, pytest.warns(AirflowProviderDeprecationWarning):
            MLEngineStartBatchPredictionJobOperator(**task_args).execute(None)
        assert str(ctx.value) == "Ambiguous model origin: Both uri and model/version name are provided."

        # Test that both uri and model/version is given
        task_args = self.BATCH_PREDICTION_DEFAULT_ARGS.copy()
        task_args["uri"] = "gs://fake-uri/saved_model"
        task_args["model_name"] = "fake_model"
        task_args["version_name"] = "fake_version"
        with pytest.raises(AirflowException) as ctx, pytest.warns(AirflowProviderDeprecationWarning):
            MLEngineStartBatchPredictionJobOperator(**task_args).execute(None)
        assert str(ctx.value) == "Ambiguous model origin: Both uri and model/version name are provided."

        # Test that a version is given without a model
        task_args = self.BATCH_PREDICTION_DEFAULT_ARGS.copy()
        task_args["version_name"] = "bare_version"
        with pytest.raises(AirflowException) as ctx, pytest.warns(AirflowProviderDeprecationWarning):
            MLEngineStartBatchPredictionJobOperator(**task_args).execute(None)
        assert (
            str(ctx.value) == "Missing model: Batch prediction expects a model "
            "name when a version name is provided."
        )

        # Test that none of uri, model, model/version is given
        task_args = self.BATCH_PREDICTION_DEFAULT_ARGS.copy()
        with pytest.raises(AirflowException) as ctx, pytest.warns(AirflowProviderDeprecationWarning):
            MLEngineStartBatchPredictionJobOperator(**task_args).execute(None)
        assert (
            str(ctx.value) == "Missing model origin: Batch prediction expects a "
            "model, a model & version combination, or a URI to a savedModel."
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_http_error(self, mock_hook):
        http_error_code = 403
        input_with_model = self.INPUT_MISSING_ORIGIN.copy()
        input_with_model["modelName"] = "projects/experimental/models/test_model"

        hook_instance = mock_hook.return_value
        hook_instance.create_job.side_effect = HttpError(
            resp=httplib2.Response({"status": http_error_code}), content=b"Forbidden"
        )
        with pytest.warns(AirflowProviderDeprecationWarning):
            prediction_task = MLEngineStartBatchPredictionJobOperator(
                job_id="test_prediction",
                project_id="test-project",
                region=input_with_model["region"],
                data_format=input_with_model["dataFormat"],
                input_paths=input_with_model["inputPaths"],
                output_path=input_with_model["outputPath"],
                model_name=input_with_model["modelName"].split("/")[-1],
                dag=self.dag,
                task_id="test-prediction",
            )
        with pytest.raises(HttpError):
            prediction_task.execute(None)
        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_failed_job_error(self, mock_hook):
        hook_instance = mock_hook.return_value
        hook_instance.create_job.return_value = {"state": "FAILED", "errorMessage": "A failure message"}
        task_args = self.BATCH_PREDICTION_DEFAULT_ARGS.copy()
        task_args["uri"] = "a uri"

        with pytest.raises(RuntimeError) as ctx, pytest.warns(AirflowProviderDeprecationWarning):
            MLEngineStartBatchPredictionJobOperator(**task_args).execute(None)

        assert str(ctx.value) == "A failure message"

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineStartBatchPredictionJobOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                job_id="{{ 'job_id' }}",
                region="{{ 'region' }}",
                input_paths="{{ 'input_paths' }}",
                output_path="{{ 'output_path' }}",
                model_name="{{ 'model_name' }}",
                version_name="{{ 'version_name' }}",
                uri="{{ 'uri' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                data_format="data_format",
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineStartBatchPredictionJobOperator = ti.task
        assert task.project_id == "project_id"
        assert task.job_id == "job_id"
        assert task.region == "region"
        assert task.input_paths == "input_paths"
        assert task.output_path == "output_path"
        assert task.model_name == "model_name"
        assert task.version_name == "version_name"
        assert task.uri == "uri"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineTrainingCancelJobOperator:
    TRAINING_DEFAULT_ARGS = {
        "project_id": "test-project",
        "job_id": "test_training",
        "task_id": "test-training",
    }

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_cancel_training_job(self, mock_hook):
        success_response = {}
        hook_instance = mock_hook.return_value
        hook_instance.cancel_job.return_value = success_response

        with pytest.warns(AirflowProviderDeprecationWarning):
            cancel_training_op = MLEngineTrainingCancelJobOperator(**self.TRAINING_DEFAULT_ARGS)
        cancel_training_op.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        # Make sure only 'cancel_job' is invoked on hook instance
        assert len(hook_instance.mock_calls) == 1
        hook_instance.cancel_job.assert_called_once_with(
            project_id=self.TRAINING_DEFAULT_ARGS["project_id"], job_id=self.TRAINING_DEFAULT_ARGS["job_id"]
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_http_error(self, mock_hook):
        http_error_code = 403
        hook_instance = mock_hook.return_value
        hook_instance.cancel_job.side_effect = HttpError(
            resp=httplib2.Response({"status": http_error_code}), content=b"Forbidden"
        )
        with pytest.warns(AirflowProviderDeprecationWarning):
            cancel_training_op = MLEngineTrainingCancelJobOperator(**self.TRAINING_DEFAULT_ARGS)
        with pytest.raises(HttpError) as ctx:
            cancel_training_op.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        # Make sure only 'cancel_job' is invoked on hook instance
        assert len(hook_instance.mock_calls) == 1
        hook_instance.cancel_job.assert_called_once_with(
            project_id=self.TRAINING_DEFAULT_ARGS["project_id"], job_id=self.TRAINING_DEFAULT_ARGS["job_id"]
        )
        assert http_error_code == ctx.value.resp.status

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineTrainingCancelJobOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                job_id="{{ 'job_id' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineTrainingCancelJobOperator = ti.task
        assert task.project_id == "project_id"
        assert task.job_id == "job_id"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineModelOperator:
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_create_model(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineManageModelOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model=TEST_MODEL,
                operation="create",
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )

        task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_model.assert_called_once_with(
            project_id=TEST_PROJECT_ID, model=TEST_MODEL
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_get_model(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineManageModelOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model=TEST_MODEL,
                operation="get",
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )

        result = task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.get_model.assert_called_once_with(
            project_id=TEST_PROJECT_ID, model_name=TEST_MODEL_NAME
        )
        assert mock_hook.return_value.get_model.return_value == result

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_fail(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineManageModelOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model=TEST_MODEL,
                operation="invalid",
                gcp_conn_id=TEST_GCP_CONN_ID,
            )
        with pytest.raises(ValueError):
            task.execute(None)

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineManageModelOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model="{{ 'model' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineManageModelOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model == "model"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineCreateModelOperator:
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_create_model(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineCreateModelOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model=TEST_MODEL,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )

        task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_model.assert_called_once_with(
            project_id=TEST_PROJECT_ID, model=TEST_MODEL
        )

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineCreateModelOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model="{{ 'model' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineCreateModelOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model == "model"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineGetModelOperator:
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_get_model(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineGetModelOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )

        result = task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.get_model.assert_called_once_with(
            project_id=TEST_PROJECT_ID, model_name=TEST_MODEL_NAME
        )
        assert mock_hook.return_value.get_model.return_value == result

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineGetModelOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model_name="{{ 'model_name' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineGetModelOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model_name == "model_name"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineDeleteModelOperator:
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_delete_model(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineDeleteModelOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
                delete_contents=True,
            )

        task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.delete_model.assert_called_once_with(
            project_id=TEST_PROJECT_ID, model_name=TEST_MODEL_NAME, delete_contents=True
        )

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineDeleteModelOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model_name="{{ 'model_name' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineDeleteModelOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model_name == "model_name"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineVersionOperator:
    VERSION_DEFAULT_ARGS = {
        "project_id": "test-project",
        "model_name": "test-model",
        "task_id": "test-version",
    }

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success_create_version(self, mock_hook):
        success_response = {"name": "some-name", "done": True}
        hook_instance = mock_hook.return_value
        hook_instance.create_version.return_value = success_response
        with pytest.warns(AirflowProviderDeprecationWarning):
            training_op = MLEngineManageVersionOperator(version=TEST_VERSION, **self.VERSION_DEFAULT_ARGS)
        training_op.execute(None)

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        # Make sure only 'create_version' is invoked on hook instance
        assert len(hook_instance.mock_calls) == 1
        hook_instance.create_version.assert_called_once_with(
            project_id="test-project", model_name="test-model", version_spec=TEST_VERSION
        )

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineManageVersionOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model_name="{{ 'model_name' }}",
                version="{{ 'version' }}",
                version_name="{{ 'version_name' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineManageVersionOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model_name == "model_name"
        assert task.version == "version"
        assert task.version_name == "version_name"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineCreateVersion:
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineCreateVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                version=TEST_VERSION,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )

        task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_version.assert_called_once_with(
            project_id=TEST_PROJECT_ID, model_name=TEST_MODEL_NAME, version_spec=TEST_VERSION
        )

    def test_missing_model_name(self):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineCreateVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=None,
                version=TEST_VERSION,
                gcp_conn_id=TEST_GCP_CONN_ID,
            )
        with pytest.raises(AirflowException):
            task.execute(context=MagicMock())

    def test_missing_version(self):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineCreateVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                version=None,
                gcp_conn_id=TEST_GCP_CONN_ID,
            )
        with pytest.raises(AirflowException):
            task.execute(context=MagicMock())

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineCreateVersionOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model_name="{{ 'model_name' }}",
                version="{{ 'version' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineCreateVersionOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model_name == "model_name"
        assert task.version == "version"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineSetDefaultVersion:
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineSetDefaultVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                version_name=TEST_VERSION_NAME,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )

        task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.set_default_version.assert_called_once_with(
            project_id=TEST_PROJECT_ID, model_name=TEST_MODEL_NAME, version_name=TEST_VERSION_NAME
        )

    def test_missing_model_name(self):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineSetDefaultVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=None,
                version_name=TEST_VERSION_NAME,
                gcp_conn_id=TEST_GCP_CONN_ID,
            )
        with pytest.raises(AirflowException):
            task.execute(context=MagicMock())

    def test_missing_version_name(self):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineSetDefaultVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                version_name=None,
                gcp_conn_id=TEST_GCP_CONN_ID,
            )
        with pytest.raises(AirflowException):
            task.execute(context=MagicMock())

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineSetDefaultVersionOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model_name="{{ 'model_name' }}",
                version_name="{{ 'version_name' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineSetDefaultVersionOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model_name == "model_name"
        assert task.version_name == "version_name"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineListVersions:
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineListVersionsOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )

        task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.list_versions.assert_called_once_with(
            project_id=TEST_PROJECT_ID,
            model_name=TEST_MODEL_NAME,
        )

    def test_missing_model_name(self):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineListVersionsOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=None,
                gcp_conn_id=TEST_GCP_CONN_ID,
            )
        with pytest.raises(AirflowException):
            task.execute(context=MagicMock())

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineListVersionsOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model_name="{{ 'model_name' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineListVersionsOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model_name == "model_name"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineDeleteVersion:
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_success(self, mock_hook):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineDeleteVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                version_name=TEST_VERSION_NAME,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )

        task.execute(context=MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.delete_version.assert_called_once_with(
            project_id=TEST_PROJECT_ID, model_name=TEST_MODEL_NAME, version_name=TEST_VERSION_NAME
        )

    def test_missing_version_name(self):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineDeleteVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=TEST_MODEL_NAME,
                version_name=None,
                gcp_conn_id=TEST_GCP_CONN_ID,
            )
        with pytest.raises(AirflowException):
            task.execute(context=MagicMock())

    def test_missing_model_name(self):
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = MLEngineDeleteVersionOperator(
                task_id="task-id",
                project_id=TEST_PROJECT_ID,
                model_name=None,
                version_name=TEST_VERSION_NAME,
                gcp_conn_id=TEST_GCP_CONN_ID,
            )
        with pytest.raises(AirflowException):
            task.execute(context=MagicMock())

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineDeleteVersionOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                model_name="{{ 'model_name' }}",
                version_name="{{ 'version_name' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineDeleteVersionOperator = ti.task
        assert task.project_id == "project_id"
        assert task.model_name == "model_name"
        assert task.version_name == "version_name"
        assert task.impersonation_chain == "impersonation_chain"


class TestMLEngineStartTrainingJobOperator:
    TRAINING_DEFAULT_ARGS = {
        "project_id": "test-project",
        "job_id": "test_training",
        "package_uris": ["gs://some-bucket/package1"],
        "training_python_module": "trainer",
        "training_args": "--some_arg='aaa'",
        "region": "us-east1",
        "scale_tier": "STANDARD_1",
        "labels": {"some": "labels"},
        "task_id": "test-training",
    }
    TRAINING_INPUT = {
        "jobId": "test_training",
        "labels": {"some": "labels"},
        "trainingInput": {
            "scaleTier": "STANDARD_1",
            "packageUris": ["gs://some-bucket/package1"],
            "pythonModule": "trainer",
            "args": "--some_arg='aaa'",
            "region": "us-east1",
        },
    }

    @patch(MLENGINE_AI_PATH.format("MLEngineStartTrainingJobOperator._wait_for_job_done"))
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_create_training_job_should_execute_successfully(self, mock_hook, mock_wait_for_job):
        mock_hook.return_value.create_job_without_waiting_result.return_value = "test_training"
        mock_wait_for_job.return_value = {"state": "SUCCEEDED"}

        with pytest.warns(AirflowProviderDeprecationWarning):
            training_op = MLEngineStartTrainingJobOperator(deferrable=False, **self.TRAINING_DEFAULT_ARGS)
        training_op.execute(MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        mock_hook.return_value.create_job_without_waiting_result.assert_called_once_with(
            project_id="test-project", body=self.TRAINING_INPUT
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineStartTrainingJobOperator._wait_for_job_done"))
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_create_training_job_with_master_config_should_execute_successfully(
        self, mock_hook, mock_wait_for_job
    ):
        custom_training_default_args: dict = copy.deepcopy(self.TRAINING_DEFAULT_ARGS)
        custom_training_default_args["scale_tier"] = "CUSTOM"

        training_input = copy.deepcopy(self.TRAINING_INPUT)
        training_input["trainingInput"]["runtimeVersion"] = "1.6"
        training_input["trainingInput"]["pythonVersion"] = "3.5"
        training_input["trainingInput"]["jobDir"] = "gs://some-bucket/jobs/test_training"
        training_input["trainingInput"]["scaleTier"] = "CUSTOM"
        training_input["trainingInput"]["masterType"] = "n1-standard-4"
        training_input["trainingInput"]["masterConfig"] = {
            "acceleratorConfig": {"count": "1", "type": "NVIDIA_TESLA_P4"},
        }

        success_response = training_input.copy()
        mock_wait_for_job.return_value = {"state": "SUCCEEDED"}
        mock_hook.return_value.create_job_without_waiting_result.return_value = success_response

        with pytest.warns(AirflowProviderDeprecationWarning):
            training_op = MLEngineStartTrainingJobOperator(
                runtime_version="1.6",
                python_version="3.5",
                job_dir="gs://some-bucket/jobs/test_training",
                master_type="n1-standard-4",
                master_config={
                    "acceleratorConfig": {"count": "1", "type": "NVIDIA_TESLA_P4"},
                },
                deferrable=False,
                **custom_training_default_args,
            )
        training_op.execute(MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        mock_hook.return_value.create_job_without_waiting_result.assert_called_once_with(
            project_id="test-project", body=training_input
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineStartTrainingJobOperator._wait_for_job_done"))
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_create_training_job_with_master_image_should_execute_successfully(
        self, mock_hook, mock_wait_for_job
    ):
        arguments = {
            "project_id": "test-project",
            "job_id": "test_training",
            "region": "europe-west1",
            "scale_tier": "CUSTOM",
            "master_type": "n1-standard-8",
            "master_config": {
                "imageUri": "eu.gcr.io/test-project/test-image:test-version",
            },
            "task_id": "test-training",
            "start_date": DEFAULT_DATE,
            "deferrable": False,
        }
        request = {
            "jobId": "test_training",
            "trainingInput": {
                "region": "europe-west1",
                "scaleTier": "CUSTOM",
                "masterType": "n1-standard-8",
                "masterConfig": {
                    "imageUri": "eu.gcr.io/test-project/test-image:test-version",
                },
            },
        }

        response = request.copy()
        mock_wait_for_job.return_value = {"state": "SUCCEEDED"}
        mock_hook.return_value.create_job_without_waiting_result.return_value = response

        with pytest.warns(AirflowProviderDeprecationWarning):
            training_op = MLEngineStartTrainingJobOperator(**arguments)
        training_op.execute(MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        mock_hook.return_value.create_job_without_waiting_result.assert_called_once_with(
            project_id="test-project",
            body=request,
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineStartTrainingJobOperator._wait_for_job_done"))
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_create_training_job_with_optional_args_should_execute_successfully(
        self, mock_hook, mock_wait_for_job
    ):
        training_input = copy.deepcopy(self.TRAINING_INPUT)
        training_input["trainingInput"]["runtimeVersion"] = "1.6"
        training_input["trainingInput"]["pythonVersion"] = "3.5"
        training_input["trainingInput"]["jobDir"] = "gs://some-bucket/jobs/test_training"
        training_input["trainingInput"]["serviceAccount"] = "test@serviceaccount.com"

        hyperparams = {
            "goal": "MAXIMIZE",
            "hyperparameterMetricTag": "metric1",
            "maxTrials": 30,
            "maxParallelTrials": 1,
            "enableTrialEarlyStopping": True,
            "params": [],
        }

        hyperparams["params"].append(
            {
                "parameterName": "hidden1",
                "type": "INTEGER",
                "minValue": 40,
                "maxValue": 400,
                "scaleType": "UNIT_LINEAR_SCALE",
            }
        )

        hyperparams["params"].append(
            {"parameterName": "numRnnCells", "type": "DISCRETE", "discreteValues": [1, 2, 3, 4]}
        )

        hyperparams["params"].append(
            {
                "parameterName": "rnnCellType",
                "type": "CATEGORICAL",
                "categoricalValues": [
                    "BasicLSTMCell",
                    "BasicRNNCell",
                    "GRUCell",
                    "LSTMCell",
                    "LayerNormBasicLSTMCell",
                ],
            }
        )

        training_input["trainingInput"]["hyperparameters"] = hyperparams

        success_response = self.TRAINING_INPUT.copy()
        mock_wait_for_job.return_value = {"state": "SUCCEEDED"}
        mock_hook.return_value.create_job_without_waiting_result.return_value = success_response

        with pytest.warns(AirflowProviderDeprecationWarning):
            training_op = MLEngineStartTrainingJobOperator(
                runtime_version="1.6",
                python_version="3.5",
                job_dir="gs://some-bucket/jobs/test_training",
                service_account="test@serviceaccount.com",
                **self.TRAINING_DEFAULT_ARGS,
                hyperparameters=hyperparams,
                deferrable=False,
            )
        training_op.execute(MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        mock_hook.return_value.create_job_without_waiting_result.assert_called_once_with(
            project_id="test-project", body=training_input
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineStartTrainingJobOperator._wait_for_job_done"))
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_create_training_job_when_http_error_409_should_execute_successfully(
        self, mock_hook, mock_wait_for_job
    ):
        mock_hook.return_value.create_job_without_waiting_result.return_value = HttpError(
            resp=httplib2.Response({"status": "409"}), content=b"content"
        )
        mock_hook.return_value.get_job.return_value = {"job_id": "test_training"}
        mock_wait_for_job.return_value = {"state": "SUCCEEDED"}

        with pytest.warns(AirflowProviderDeprecationWarning):
            training_op = MLEngineStartTrainingJobOperator(**self.TRAINING_DEFAULT_ARGS)
        training_op.execute(MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_create_training_job_should_throw_exception_when_http_error_403(self, mock_hook):
        mock_hook.return_value.create_job_without_waiting_result.side_effect = HttpError(
            resp=httplib2.Response({"status": "403"}), content=b"content"
        )

        with pytest.warns(AirflowProviderDeprecationWarning):
            training_op = MLEngineStartTrainingJobOperator(**self.TRAINING_DEFAULT_ARGS)
        with pytest.raises(HttpError):
            training_op.execute(MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )

    @patch(MLENGINE_AI_PATH.format("MLEngineStartTrainingJobOperator._wait_for_job_done"))
    @patch(MLENGINE_AI_PATH.format("MLEngineHook"))
    def test_create_training_job_should_throw_exception_when_job_failed(self, mock_hook, mock_wait_for_job):
        failure_response = self.TRAINING_INPUT.copy()

        mock_wait_for_job.return_value = {"state": "FAILED", "errorMessage": "A failure message"}
        mock_hook.return_value.create_job_without_waiting_result.return_value = failure_response

        with pytest.warns(AirflowProviderDeprecationWarning):
            training_op = MLEngineStartTrainingJobOperator(**self.TRAINING_DEFAULT_ARGS)
        with pytest.raises(RuntimeError) as ctx:
            training_op.execute(MagicMock())

        mock_hook.assert_called_once_with(
            gcp_conn_id="google_cloud_default",
            impersonation_chain=None,
        )
        mock_hook.return_value.create_job_without_waiting_result.assert_called_once_with(
            project_id="test-project", body=self.TRAINING_INPUT
        )
        assert str(ctx.value) == "A failure message"

    @pytest.mark.db_test
    def test_templating(self, create_task_instance_of_operator, session):
        with pytest.warns(AirflowProviderDeprecationWarning):
            ti = create_task_instance_of_operator(
                MLEngineStartTrainingJobOperator,
                # Templated fields
                project_id="{{ 'project_id' }}",
                job_id="{{ 'job_id' }}",
                region="{{ 'region' }}",
                package_uris="{{ 'package_uris' }}",
                training_python_module="{{ 'training_python_module' }}",
                training_args="{{ 'training_args' }}",
                scale_tier="{{ 'scale_tier' }}",
                master_type="{{ 'master_type' }}",
                master_config="{{ 'master_config' }}",
                runtime_version="{{ 'runtime_version' }}",
                python_version="{{ 'python_version' }}",
                job_dir="{{ 'job_dir' }}",
                service_account="{{ 'service_account' }}",
                hyperparameters="{{ 'hyperparameters' }}",
                impersonation_chain="{{ 'impersonation_chain' }}",
                # Other parameters
                dag_id="test_template_body_templating_dag",
                task_id="test_template_body_templating_task",
            )
        session.add(ti)
        session.commit()
        ti.render_templates()
        task: MLEngineStartTrainingJobOperator = ti.task
        assert task.project_id == "project_id"
        assert task.job_id == "job_id"
        assert task.region == "region"
        assert task.package_uris == "package_uris"
        assert task.training_python_module == "training_python_module"
        assert task.training_args == "training_args"
        assert task.scale_tier == "scale_tier"
        assert task.master_type == "master_type"
        assert task.master_config == "master_config"
        assert task.runtime_version == "runtime_version"
        assert task.python_version == "python_version"
        assert task.job_dir == "job_dir"
        assert task.service_account == "service_account"
        assert task.hyperparameters == "hyperparameters"
        assert task.impersonation_chain == "impersonation_chain"


TEST_TASK_ID = "training"
TEST_JOB_ID = "1234"
TEST_GCP_PROJECT_ID = "test-project"
TEST_REGION = "us-central1"
TEST_RUNTIME_VERSION = "1.15"
TEST_PYTHON_VERSION = "3.9"
TEST_JOB_DIR = "gs://example_mlengine_bucket/job-dir"
TEST_PACKAGE_URIS = ["gs://system-tests-resources/example_gcp_mlengine/trainer-0.1.tar.gz"]
TEST_TRAINING_PYTHON_MODULE = "trainer.task"
TEST_TRAINING_ARGS: list[str] = []
TEST_LABELS = {"job_type": "training", "***-version": "v2-5-0-dev0"}


@pytest.mark.db_test
@patch(MLENGINE_AI_PATH.format("MLEngineHook"))
def test_async_create_training_job_should_execute_successfully(
    mock_hook, create_task_instance_of_operator, session
):
    """
    Asserts that a task is deferred and a MLEngineStartTrainingJobTrigger will be fired
    when the MLEngineStartTrainingJobOperator is executed in deferrable mode when deferrable=True.
    """
    mock_hook.return_value.create_job_without_waiting_result.return_value = "test_training"

    with pytest.warns(AirflowProviderDeprecationWarning):
        ti = create_task_instance_of_operator(
            task_id=TEST_TASK_ID,
            project_id=TEST_GCP_PROJECT_ID,
            region=TEST_REGION,
            job_id=TEST_JOB_ID,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=TEST_PACKAGE_URIS,
            training_python_module=TEST_TRAINING_PYTHON_MODULE,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            deferrable=True,
            operator_class=MLEngineStartTrainingJobOperator,
            dag_id="test_async_create_training",
        )

    with pytest.raises(TaskDeferred) as exc:
        ti.task.execute({"ti": ti})

    assert isinstance(exc.value.trigger, MLEngineStartTrainingJobTrigger), (
        "Trigger is not a MLEngineStartTrainingJobTrigger"
    )


def test_async_create_training_job_should_throw_exception():
    """Tests that an AirflowException is raised in case of error event"""

    with pytest.warns(AirflowProviderDeprecationWarning):
        op = MLEngineStartTrainingJobOperator(
            task_id=TEST_TASK_ID,
            project_id=TEST_GCP_PROJECT_ID,
            region=TEST_REGION,
            job_id=TEST_JOB_ID,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=TEST_PACKAGE_URIS,
            training_python_module=TEST_TRAINING_PYTHON_MODULE,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            deferrable=True,
        )

    with pytest.raises(AirflowException):
        op.execute_complete(context=None, event={"status": "error", "message": "test failure message"})


def create_context(task):
    dag = DAG(dag_id="dag", schedule=None)
    logical_date = datetime(2022, 1, 1, 0, 0, 0)
    dag_run = DagRun(
        dag_id=dag.dag_id,
        logical_date=logical_date,
        run_id=DagRun.generate_run_id(DagRunType.MANUAL, logical_date),
    )
    task_instance = TaskInstance(task=task)
    task_instance.dag_run = dag_run
    task_instance.dag_id = dag.dag_id
    task_instance.xcom_push = MagicMock()
    return {
        "dag": dag,
        "run_id": dag_run.run_id,
        "task": task,
        "ti": task_instance,
        "task_instance": task_instance,
        "logical_date": logical_date,
    }


@pytest.mark.db_test
def test_async_create_training_job_logging_should_execute_successfully(
    create_task_instance_of_operator, session
):
    """Asserts that logging occurs as expected"""

    with pytest.warns(AirflowProviderDeprecationWarning):
        ti = create_task_instance_of_operator(
            operator_class=MLEngineStartTrainingJobOperator,
            task_id=TEST_TASK_ID,
            project_id=TEST_GCP_PROJECT_ID,
            region=TEST_REGION,
            job_id=TEST_JOB_ID,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=TEST_PACKAGE_URIS,
            training_python_module=TEST_TRAINING_PYTHON_MODULE,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            deferrable=True,
            dag_id="test_async_create_training_job_logging",
        )

    with mock.patch.object(ti.task.log, "info") as mock_log_info:
        ti.task.execute_complete(
            context={"ti": ti},
            event={"status": "success", "message": "Job completed", "job_id": TEST_TASK_ID},
        )

    mock_log_info.assert_called_with("%s completed with response %s ", TEST_TASK_ID, "Job completed")


@pytest.mark.db_test
@patch(MLENGINE_AI_PATH.format("MLEngineHook"))
def test_async_create_training_job_with_conflict_should_execute_successfully(
    mock_hook, create_task_instance_of_operator, session
):
    """Test that the operator defers correctly when a conflict occurs."""

    mock_hook.return_value.create_job_without_waiting_result.side_effect = HttpError(
        resp=httplib2.Response({"status": "409"}), content=b"some bytes"
    )
    mock_hook.return_value.get_job.return_value = {"job_id": "test_training"}

    with pytest.warns(AirflowProviderDeprecationWarning):
        ti = create_task_instance_of_operator(
            operator_class=MLEngineStartTrainingJobOperator,
            task_id=TEST_TASK_ID,
            project_id=TEST_GCP_PROJECT_ID,
            region=TEST_REGION,
            job_id=TEST_JOB_ID,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=TEST_PACKAGE_URIS,
            training_python_module=TEST_TRAINING_PYTHON_MODULE,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            deferrable=True,
            dag_id="test_async_create_training_job_with_conflict",
        )

    with pytest.raises(TaskDeferred):
        ti.task.execute({"ti": ti})

    mock_hook.assert_called_once_with(
        gcp_conn_id="google_cloud_default",
        impersonation_chain=None,
    )
    mock_hook.return_value.create_job_without_waiting_result.assert_called_once()


@pytest.mark.db_test
def test_async_create_training_job_should_throw_exception_if_job_id_none(
    create_task_instance_of_operator, session
):
    """Test that the operator throws an exception if the job_id is None."""

    with pytest.warns(AirflowProviderDeprecationWarning):
        ti = create_task_instance_of_operator(
            operator_class=MLEngineStartTrainingJobOperator,
            task_id=TEST_TASK_ID,
            project_id=TEST_GCP_PROJECT_ID,
            region=TEST_REGION,
            job_id=None,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=TEST_PACKAGE_URIS,
            training_python_module=TEST_TRAINING_PYTHON_MODULE,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            deferrable=True,
            dag_id="test_async_create_training_job",
        )

    with pytest.raises(
        AirflowException, match=r"An unique job id is required for Google MLEngine training job."
    ):
        ti.task.execute({"ti": ti})


@pytest.mark.db_test
def test_async_create_training_job_should_throw_exception_if_project_id_none(
    create_task_instance_of_operator, session
):
    """Test that the operator throws an exception if the project_id is None."""
    with pytest.warns(AirflowProviderDeprecationWarning):
        ti = create_task_instance_of_operator(
            operator_class=MLEngineStartTrainingJobOperator,
            task_id=TEST_TASK_ID,
            project_id=None,
            region=TEST_REGION,
            job_id=TEST_JOB_ID,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=TEST_PACKAGE_URIS,
            training_python_module=TEST_TRAINING_PYTHON_MODULE,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            deferrable=True,
            dag_id="test_async_create_training_job_exception",
        )

    with pytest.raises(AirflowException, match=r"Google Cloud project id is required."):
        ti.task.execute({"ti": ti})


@pytest.mark.db_test
def test_async_create_training_job_should_throw_exception_if_custom_none(
    create_task_instance_of_operator, session
):
    """Test that the operator throws an exception if master_type is None while master_config is provided."""
    with pytest.warns(AirflowProviderDeprecationWarning):
        ti = create_task_instance_of_operator(
            operator_class=MLEngineStartTrainingJobOperator,
            task_id=TEST_TASK_ID,
            project_id=TEST_PROJECT_ID,
            region=TEST_REGION,
            job_id=TEST_JOB_ID,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=TEST_PACKAGE_URIS,
            training_python_module=TEST_TRAINING_PYTHON_MODULE,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            master_config={"config": "config"},
            master_type=None,
            deferrable=True,
            dag_id="test_async_create_training_job_custom",
        )

    with pytest.raises(AirflowException, match=r"master_type must be set when master_config is provided"):
        ti.task.execute({"ti": ti})


@pytest.mark.db_test
def test_async_create_training_job_should_throw_exception_if_package_none(
    create_task_instance_of_operator, session
):
    """Test that the operator throws an exception if both package_uris and training_python_module are None."""

    with pytest.warns(AirflowProviderDeprecationWarning):
        ti = create_task_instance_of_operator(
            operator_class=MLEngineStartTrainingJobOperator,
            task_id=TEST_TASK_ID,
            project_id=TEST_PROJECT_ID,
            region=TEST_REGION,
            job_id=TEST_JOB_ID,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=None,
            training_python_module=None,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            deferrable=True,
            dag_id="test_async_create_training_job_package",
        )

    with pytest.raises(
        AirflowException,
        match=r"Either a Python package with a Python module or a custom "
        r"Docker image should be provided.",
    ):
        ti.task.execute({"ti": ti})


@pytest.mark.db_test
def test_async_create_training_job_should_throw_exception_if_uris_none(
    create_task_instance_of_operator, session
):
    """Test that the operator throws an exception if package_uris is None."""

    with pytest.warns(AirflowProviderDeprecationWarning):
        ti = create_task_instance_of_operator(
            operator_class=MLEngineStartTrainingJobOperator,
            task_id=TEST_TASK_ID,
            project_id=TEST_PROJECT_ID,
            region=TEST_REGION,
            job_id=TEST_JOB_ID,
            runtime_version=TEST_RUNTIME_VERSION,
            python_version=TEST_PYTHON_VERSION,
            job_dir=TEST_JOB_DIR,
            package_uris=None,
            training_python_module=TEST_TRAINING_PYTHON_MODULE,
            training_args=TEST_TRAINING_ARGS,
            labels=TEST_LABELS,
            master_config={"config": "config"},
            master_type="type",
            deferrable=True,
            dag_id="test_async_create_training_job_with_uri",
        )

    with pytest.raises(
        AirflowException,
        match=r"Either a Python package with a Python module or a custom "
        r"Docker image should be provided.",
    ):
        ti.task.execute({"ti": ti})
