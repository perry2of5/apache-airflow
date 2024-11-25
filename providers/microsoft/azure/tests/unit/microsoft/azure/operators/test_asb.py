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

from unittest import mock

import pytest
from azure.core.exceptions import ResourceExistsError
from azure.servicebus import ServiceBusMessage

try:
    from azure.servicebus import ServiceBusMessage
except ImportError:
    pytest.skip("Azure Service Bus not available", allow_module_level=True)

from azure.core.exceptions import ResourceNotFoundError

from airflow.providers.microsoft.azure.hooks.asb import MessageHook
from airflow.providers.microsoft.azure.operators.asb import (
    ASBReceiveSubscriptionMessageOperator,
    AzureServiceBusCreateQueueOperator,
    AzureServiceBusDeleteQueueOperator,
    AzureServiceBusReceiveMessageOperator,
    AzureServiceBusRequestReplyOperator,
    AzureServiceBusSendMessageOperator,
    AzureServiceBusSubscriptionCreateOperator,
    AzureServiceBusSubscriptionDeleteOperator,
    AzureServiceBusTopicCreateOperator,
    AzureServiceBusTopicDeleteOperator,
    AzureServiceBusUpdateSubscriptionOperator,
)

try:
    from airflow.sdk.definitions.context import Context
except ImportError:
    # TODO: Remove once provider drops support for Airflow 2
    from airflow.utils.context import Context

QUEUE_NAME = "test_queue"
MESSAGE = "Test Message"
MESSAGE_LIST = [f"MESSAGE {n}" for n in range(10)]

OWNER_NAME = "airflow"
DAG_ID = "test_azure_service_bus_subscription"
TOPIC_NAME = "sb_mgmt_topic_test"
SUBSCRIPTION_NAME = "sb_mgmt_subscription"


class TestAzureServiceBusCreateQueueOperator:
    @pytest.mark.parametrize(
        "mock_dl_msg_expiration, mock_batched_operation",
        [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ],
    )
    def test_init(self, mock_dl_msg_expiration, mock_batched_operation):
        """
        Test init by creating AzureServiceBusCreateQueueOperator with task id,
        queue_name and asserting with value
        """
        asb_create_queue_operator = AzureServiceBusCreateQueueOperator(
            task_id="asb_create_queue",
            queue_name=QUEUE_NAME,
            max_delivery_count=10,
            dead_lettering_on_message_expiration=mock_dl_msg_expiration,
            enable_batched_operations=mock_batched_operation,
        )
        assert asb_create_queue_operator.task_id == "asb_create_queue"
        assert asb_create_queue_operator.queue_name == QUEUE_NAME
        assert asb_create_queue_operator.max_delivery_count == 10
        assert asb_create_queue_operator.dead_lettering_on_message_expiration is mock_dl_msg_expiration
        assert asb_create_queue_operator.enable_batched_operations is mock_batched_operation

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook.get_conn")
    def test_create_queue(self, mock_get_conn):
        """
        Test AzureServiceBusCreateQueueOperator passed with the queue name,
        mocking the connection details, hook create_queue function
        """
        asb_create_queue_operator = AzureServiceBusCreateQueueOperator(
            task_id="asb_create_queue_operator",
            queue_name=QUEUE_NAME,
            max_delivery_count=10,
            dead_lettering_on_message_expiration=True,
            enable_batched_operations=True,
        )
        asb_create_queue_operator.execute(None)
        mock_get_conn.return_value.__enter__.return_value.create_queue.assert_called_once_with(
            QUEUE_NAME,
            max_delivery_count=10,
            dead_lettering_on_message_expiration=True,
            enable_batched_operations=True,
        )


class TestAzureServiceBusDeleteQueueOperator:
    def test_init(self):
        """
        Test init by creating AzureServiceBusDeleteQueueOperator with task id, queue_name and asserting
        with values
        """
        asb_delete_queue_operator = AzureServiceBusDeleteQueueOperator(
            task_id="asb_delete_queue",
            queue_name=QUEUE_NAME,
        )
        assert asb_delete_queue_operator.task_id == "asb_delete_queue"
        assert asb_delete_queue_operator.queue_name == QUEUE_NAME

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook.get_conn")
    def test_delete_queue(self, mock_get_conn):
        """Test AzureServiceBusDeleteQueueOperator by mocking queue name, connection and hook delete_queue"""
        asb_delete_queue_operator = AzureServiceBusDeleteQueueOperator(
            task_id="asb_delete_queue",
            queue_name=QUEUE_NAME,
        )
        asb_delete_queue_operator.execute(None)
        mock_get_conn.return_value.__enter__.return_value.delete_queue.assert_called_once_with(QUEUE_NAME)


class TestAzureServiceBusSendMessageOperator:
    @pytest.mark.parametrize(
        "mock_message, mock_batch_flag",
        [
            (MESSAGE, True),
            (MESSAGE, False),
            (MESSAGE_LIST, True),
            (MESSAGE_LIST, False),
        ],
    )
    def test_init(self, mock_message, mock_batch_flag):
        """
        Test init by creating AzureServiceBusSendMessageOperator with task id, queue_name, message,
        batch and asserting with values
        """
        asb_send_message_queue_operator = AzureServiceBusSendMessageOperator(
            task_id="asb_send_message_queue_without_batch",
            queue_name=QUEUE_NAME,
            message=mock_message,
            batch=mock_batch_flag,
        )
        assert asb_send_message_queue_operator.task_id == "asb_send_message_queue_without_batch"
        assert asb_send_message_queue_operator.queue_name == QUEUE_NAME
        assert asb_send_message_queue_operator.message == mock_message
        assert asb_send_message_queue_operator.batch is mock_batch_flag

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.MessageHook.get_conn")
    def test_send_message_queue(self, mock_get_conn):
        """
        Test AzureServiceBusSendMessageOperator with queue name, batch boolean flag, mock
        the send_messages of azure service bus function
        """
        asb_send_message_queue_operator = AzureServiceBusSendMessageOperator(
            task_id="asb_send_message_queue",
            queue_name=QUEUE_NAME,
            message="Test message",
            batch=False,
        )
        asb_send_message_queue_operator.execute(None)
        expected_calls = [
            mock.call()
            .__enter__()
            .get_queue_sender(QUEUE_NAME)
            .__enter__()
            .send_messages(ServiceBusMessage("Test message"))
            .__exit__()
        ]
        mock_get_conn.assert_has_calls(expected_calls, any_order=False)


class TestAzureServiceBusReceiveMessageOperator:
    def test_init(self):
        """
        Test init by creating AzureServiceBusReceiveMessageOperator with task id, queue_name, message,
        batch and asserting with values
        """

        asb_receive_queue_operator = AzureServiceBusReceiveMessageOperator(
            task_id="asb_receive_message_queue",
            queue_name=QUEUE_NAME,
        )
        assert asb_receive_queue_operator.task_id == "asb_receive_message_queue"
        assert asb_receive_queue_operator.queue_name == QUEUE_NAME

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.MessageHook.get_conn")
    def test_receive_message_queue(self, mock_get_conn):
        """
        Test AzureServiceBusReceiveMessageOperator by mock connection, values
        and the service bus receive message
        """
        asb_receive_queue_operator = AzureServiceBusReceiveMessageOperator(
            task_id="asb_receive_message_queue",
            queue_name=QUEUE_NAME,
        )
        asb_receive_queue_operator.execute(None)
        expected_calls = [
            mock.call()
            .__enter__()
            .get_queue_receiver(QUEUE_NAME)
            .__enter__()
            .receive_messages(max_message_count=10, max_wait_time=5)
            .get_queue_receiver(QUEUE_NAME)
            .__exit__()
            .mock_call()
            .__exit__
        ]
        mock_get_conn.assert_has_calls(expected_calls)

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.MessageHook.get_conn")
    def test_receive_message_queue_callback(self, mock_get_conn):
        """
        Test AzureServiceBusReceiveMessageOperator by mock connection, values
        and the service bus receive message
        """
        mock_service_bus_message = ServiceBusMessage("Test message with context")
        mock_get_conn.return_value.__enter__.return_value.get_queue_receiver.return_value.__enter__.return_value.receive_messages.return_value = [
            mock_service_bus_message
        ]

        messages_received = []

        def message_callback(msg: ServiceBusMessage, context: Context):
            messages_received.append(msg)
            assert context is not None
            print(msg)

        asb_receive_queue_operator = AzureServiceBusReceiveMessageOperator(
            task_id="asb_receive_message_queue", queue_name=QUEUE_NAME, message_callback=message_callback
        )
        asb_receive_queue_operator.execute(Context())
        assert len(messages_received) == 1
        assert messages_received[0] == mock_service_bus_message


class TestABSTopicCreateOperator:
    def test_init(self):
        """
        Test init by creating AzureServiceBusTopicCreateOperator with task id and topic name,
        by asserting the value
        """
        asb_create_topic = AzureServiceBusTopicCreateOperator(
            task_id="asb_create_topic",
            topic_name=TOPIC_NAME,
        )
        assert asb_create_topic.task_id == "asb_create_topic"
        assert asb_create_topic.topic_name == TOPIC_NAME

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook.get_conn")
    @mock.patch("azure.servicebus.management.TopicProperties")
    def test_create_topic(self, mock_topic_properties, mock_get_conn):
        """
        Test AzureServiceBusTopicCreateOperator passed with the topic name
        mocking the connection
        """
        asb_create_topic = AzureServiceBusTopicCreateOperator(
            task_id="asb_create_topic",
            topic_name=TOPIC_NAME,
        )
        mock_topic_properties.name = TOPIC_NAME
        mock_get_conn.return_value.__enter__.return_value.create_topic.return_value = mock_topic_properties
        # create the topic
        created_topic_name = asb_create_topic.execute(None)
        # ensure the topic name is returned
        assert created_topic_name == TOPIC_NAME
        # ensure create_topic is called with the correct arguments on the connection
        mock_get_conn.return_value.__enter__.return_value.create_topic.assert_called_once_with(
            topic_name=TOPIC_NAME,
            default_message_time_to_live=None,
            max_size_in_megabytes=None,
            requires_duplicate_detection=None,
            duplicate_detection_history_time_window=None,
            enable_batched_operations=None,
            size_in_bytes=None,
            filtering_messages_before_publishing=None,
            authorization_rules=None,
            support_ordering=None,
            auto_delete_on_idle=None,
            enable_partitioning=None,
            enable_express=None,
            user_metadata=None,
            max_message_size_in_kilobytes=None,
        )

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook")
    def test_create_topic_exception(self, mock_sb_admin_client):
        """
        Test `AzureServiceBusTopicCreateOperator` functionality to raise AirflowException,
         by passing topic name as None and pytest raise Airflow Exception
        """
        asb_create_topic_exception = AzureServiceBusTopicCreateOperator(
            task_id="create_service_bus_subscription",
            topic_name=None,
        )
        with pytest.raises(TypeError):
            asb_create_topic_exception.execute(None)


class TestASBCreateSubscriptionOperator:
    def test_init(self):
        """
        Test init by creating ASBCreateSubscriptionOperator with task id, subscription name, topic name and
        asserting with value
        """
        asb_create_subscription = AzureServiceBusSubscriptionCreateOperator(
            task_id="asb_create_subscription",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
        )
        assert asb_create_subscription.task_id == "asb_create_subscription"
        assert asb_create_subscription.subscription_name == SUBSCRIPTION_NAME
        assert asb_create_subscription.topic_name == TOPIC_NAME

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook.get_conn")
    @mock.patch("azure.servicebus.management.SubscriptionProperties")
    def test_create_subscription(self, mock_subscription_properties, mock_get_conn):
        """
        Test AzureServiceBusSubscriptionCreateOperator passed with the subscription name, topic name
        mocking the connection details, hook create_subscription function
        """
        asb_create_subscription = AzureServiceBusSubscriptionCreateOperator(
            task_id="create_service_bus_subscription",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
        )
        mock_subscription_properties.name = SUBSCRIPTION_NAME
        mock_subscription_properties.to = SUBSCRIPTION_NAME
        mock_get_conn.return_value.__enter__.return_value.create_subscription.return_value = (
            mock_subscription_properties
        )

        with mock.patch.object(asb_create_subscription.log, "info") as mock_log_info:
            asb_create_subscription.execute(None)
        mock_log_info.assert_called_with("Created subscription %s", SUBSCRIPTION_NAME)

    @pytest.mark.parametrize(
        "mock_subscription_name, mock_topic_name",
        [("subscription_1", None), (None, "topic_1")],
    )
    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook")
    def test_create_subscription_exception(
        self, mock_sb_admin_client, mock_subscription_name, mock_topic_name
    ):
        """
        Test `AzureServiceBusSubscriptionCreateOperator` functionality to raise AirflowException,
         by passing subscription name and topic name as None and pytest raise Airflow Exception
        """
        asb_create_subscription = AzureServiceBusSubscriptionCreateOperator(
            task_id="create_service_bus_subscription",
            topic_name=mock_topic_name,
            subscription_name=mock_subscription_name,
        )
        with pytest.raises(TypeError):
            asb_create_subscription.execute(None)


class TestASBDeleteSubscriptionOperator:
    def test_init(self):
        """
        Test init by creating AzureServiceBusSubscriptionDeleteOperator with task id, subscription name,
        topic name and asserting with values
        """
        asb_delete_subscription_operator = AzureServiceBusSubscriptionDeleteOperator(
            task_id="asb_delete_subscription",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
        )
        assert asb_delete_subscription_operator.task_id == "asb_delete_subscription"
        assert asb_delete_subscription_operator.topic_name == TOPIC_NAME
        assert asb_delete_subscription_operator.subscription_name == SUBSCRIPTION_NAME

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook.get_conn")
    def test_delete_subscription(self, mock_get_conn):
        """
        Test AzureServiceBusSubscriptionDeleteOperator by mocking subscription name, topic name and
         connection and hook delete_subscription
        """
        asb_delete_subscription_operator = AzureServiceBusSubscriptionDeleteOperator(
            task_id="asb_delete_subscription",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
        )
        asb_delete_subscription_operator.execute(None)
        mock_get_conn.return_value.__enter__.return_value.delete_subscription.assert_called_once_with(
            TOPIC_NAME, SUBSCRIPTION_NAME
        )


class TestAzureServiceBusUpdateSubscriptionOperator:
    def test_init(self):
        """
        Test init by creating AzureServiceBusUpdateSubscriptionOperator with task id, subscription name,
        topic name and asserting with values
        """
        asb_update_subscription_operator = AzureServiceBusUpdateSubscriptionOperator(
            task_id="asb_update_subscription",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
            max_delivery_count=10,
        )
        assert asb_update_subscription_operator.task_id == "asb_update_subscription"
        assert asb_update_subscription_operator.topic_name == TOPIC_NAME
        assert asb_update_subscription_operator.subscription_name == SUBSCRIPTION_NAME
        assert asb_update_subscription_operator.max_delivery_count == 10

    @mock.patch("azure.servicebus.management.SubscriptionProperties")
    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook.get_conn")
    def test_update_subscription(self, mock_get_conn, mock_subscription_properties):
        """
        Test AzureServiceBusUpdateSubscriptionOperator passed with the subscription name, topic name
        mocking the connection details, hook update_subscription function
        """
        mock_subscription_properties.name = SUBSCRIPTION_NAME
        mock_subscription_properties.max_delivery_count = 20
        mock_get_conn.return_value.__enter__.return_value.get_subscription.return_value = (
            mock_subscription_properties
        )
        asb_update_subscription = AzureServiceBusUpdateSubscriptionOperator(
            task_id="asb_update_subscription",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
            max_delivery_count=20,
        )

        asb_update_subscription.execute(None)

        mock_get_conn.return_value.__enter__.return_value.get_subscription.assert_has_calls(
            [
                mock.call(TOPIC_NAME, SUBSCRIPTION_NAME),  # before update
                mock.call(TOPIC_NAME, SUBSCRIPTION_NAME),  # after update
            ]
        )

        mock_get_conn.return_value.__enter__.return_value.update_subscription.assert_called_once_with(
            TOPIC_NAME,
            mock_subscription_properties,
        )


class TestASBSubscriptionReceiveMessageOperator:
    def test_init(self):
        """
        Test init by creating ASBReceiveSubscriptionMessageOperator with task id, topic_name,
        subscription_name, batch and asserting with values
        """

        asb_subscription_receive_message = ASBReceiveSubscriptionMessageOperator(
            task_id="asb_subscription_receive_message",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
            max_message_count=10,
        )
        assert asb_subscription_receive_message.task_id == "asb_subscription_receive_message"
        assert asb_subscription_receive_message.topic_name == TOPIC_NAME
        assert asb_subscription_receive_message.subscription_name == SUBSCRIPTION_NAME
        assert asb_subscription_receive_message.max_message_count == 10

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.MessageHook.get_conn")
    def test_receive_message_queue(self, mock_get_conn):
        """
        Test ASBReceiveSubscriptionMessageOperator by mock connection, values
        and the service bus receive message
        """
        asb_subscription_receive_message = ASBReceiveSubscriptionMessageOperator(
            task_id="asb_subscription_receive_message",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
            max_message_count=10,
        )
        asb_subscription_receive_message.execute(None)
        expected_calls = [
            mock.call()
            .__enter__()
            .get_subscription_receiver(SUBSCRIPTION_NAME, TOPIC_NAME)
            .__enter__()
            .receive_messages(max_message_count=10, max_wait_time=5)
            .get_subscription_receiver(SUBSCRIPTION_NAME, TOPIC_NAME)
            .__exit__()
            .mock_call()
            .__exit__
        ]
        mock_get_conn.assert_has_calls(expected_calls)

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.MessageHook.get_conn")
    def test_receive_message_queue_callback(self, mock_get_conn):
        """
        Test ASBReceiveSubscriptionMessageOperator by mock connection, values
        and the service bus receive message
        """

        mock_sb_message0 = ServiceBusMessage("Test message 0")
        mock_sb_message1 = ServiceBusMessage("Test message 1")
        mock_get_conn.return_value.__enter__.return_value.get_subscription_receiver.return_value.__enter__.return_value.receive_messages.return_value = [
            mock_sb_message0,
            mock_sb_message1,
        ]

        messages_received = []

        def message_callback(msg: ServiceBusMessage, context: Context):
            messages_received.append(msg)
            assert context is not None
            print(msg)

        asb_subscription_receive_message = ASBReceiveSubscriptionMessageOperator(
            task_id="asb_subscription_receive_message",
            topic_name=TOPIC_NAME,
            subscription_name=SUBSCRIPTION_NAME,
            max_message_count=10,
            message_callback=message_callback,
        )

        asb_subscription_receive_message.execute(Context())
        expected_calls = [
            mock.call()
            .__enter__()
            .get_subscription_receiver(SUBSCRIPTION_NAME, TOPIC_NAME)
            .__enter__()
            .receive_messages(max_message_count=10, max_wait_time=5)
            .get_subscription_receiver(SUBSCRIPTION_NAME, TOPIC_NAME)
            .__exit__()
            .mock_call()
            .__exit__
        ]
        mock_get_conn.assert_has_calls(expected_calls)
        assert len(messages_received) == 2
        assert messages_received[0] == mock_sb_message0
        assert messages_received[1] == mock_sb_message1


class TestASBTopicDeleteOperator:
    def test_init(self):
        """
        Test init by creating AzureServiceBusTopicDeleteOperator with task id, topic name and asserting
        with values
        """
        asb_delete_topic_operator = AzureServiceBusTopicDeleteOperator(
            task_id="asb_delete_topic",
            topic_name=TOPIC_NAME,
        )
        assert asb_delete_topic_operator.task_id == "asb_delete_topic"
        assert asb_delete_topic_operator.topic_name == TOPIC_NAME

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook.get_conn")
    @mock.patch("azure.servicebus.management.TopicProperties")
    def test_delete_topic(self, mock_topic_properties, mock_get_conn):
        """
        Test AzureServiceBusTopicDeleteOperator by mocking topic name, connection
        """
        asb_delete_topic = AzureServiceBusTopicDeleteOperator(
            task_id="asb_delete_topic",
            topic_name=TOPIC_NAME,
        )
        mock_topic_properties.name = TOPIC_NAME
        mock_get_conn.return_value.__enter__.return_value.get_topic.return_value = mock_topic_properties
        with mock.patch.object(asb_delete_topic.log, "info") as mock_log_info:
            asb_delete_topic.execute(None)
        mock_log_info.assert_called_with("Topic %s deleted.", TOPIC_NAME)

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook.get_conn")
    def test_delete_topic_not_exists(self, mock_get_conn):
        """
        Test AzureServiceBusTopicDeleteOperator by mocking topic name, connection
        """
        asb_delete_topic_not_exists = AzureServiceBusTopicDeleteOperator(
            task_id="asb_delete_topic_not_exists",
            topic_name=TOPIC_NAME,
        )
        mock_get_conn.return_value.__enter__.return_value.get_topic.return_value = None
        with mock.patch.object(asb_delete_topic_not_exists.log, "info") as mock_log_info:
            asb_delete_topic_not_exists.execute(None)
        mock_log_info.assert_called_with("Topic %s does not exist.", TOPIC_NAME)

    @mock.patch("airflow.providers.microsoft.azure.hooks.asb.AdminClientHook")
    def test_delete_topic_exception(self, mock_sb_admin_client):
        """
        Test `delete_topic` functionality to raise AirflowException,
         by passing topic name as None and pytest raise Airflow Exception
        """
        asb_delete_topic_exception = AzureServiceBusTopicDeleteOperator(
            task_id="delete_service_bus_subscription",
            topic_name=None,
        )
        with pytest.raises(TypeError):
            asb_delete_topic_exception.execute(None)


class TestAzureServiceBusRequestReplyOperator:
    # tests for AzureServiceBusRequestReplyOperator._remove_reply_subscription
    # use mock for the admin_hook passed into _remove_reply_subscription to
    # ensure delete_subscription is called with correct parameters
    def test_remove_reply_subscription(self):
        with mock.patch("airflow.providers.microsoft.azure.operators.asb.AdminClientHook") as mock_admin_hook:
            operator = AzureServiceBusRequestReplyOperator(
                task_id="test_task",
                request_queue_name="test_queue",
                request_body_generator=lambda: "test_body",
                reply_topic_name="reply-topic-name",
            )

            # Set the subscription_name attribute for the operator
            operator.subscription_name = "test_subscription"

            operator._remove_reply_subscription(mock_admin_hook)

            mock_admin_hook.delete_subscription.assert_called_once_with(
                operator.subscription_name, operator.reply_topic_name
            )

    def test_remove_reply_subscription_ignores_resource_not_found_error(self):
        with mock.patch("airflow.providers.microsoft.azure.operators.asb.AdminClientHook") as mock_admin_hook:
            operator = AzureServiceBusRequestReplyOperator(
                task_id="test_task",
                request_queue_name="test_queue",
                request_body_generator=lambda: "test_body",
                reply_topic_name="reply-topic-name",
            )

            # Set the subscription_name attribute for the operator
            operator.subscription_name = "test_subscription"

            # Mock the delete_subscription method to raise ResourceNotFoundError
            mock_admin_hook.delete_subscription.side_effect = ResourceNotFoundError

            operator._remove_reply_subscription(mock_admin_hook)

            mock_admin_hook.delete_subscription.assert_called_once_with(
                operator.subscription_name, operator.reply_topic_name
            )

    # tests for AzureServiceBusRequestReplyOperator._validate_params with different combinations of parameters
    # and expected results
    @pytest.mark.parametrize(
        "request_queue_name, request_body_generator, reply_topic_name, expected_exception, expected_message",
        [
            (None, lambda: "test_body", "test_topic", TypeError, "Request queue name is required. "),
            ("test_queue", None, "test_topic", TypeError, "Request body creator is required. "),
            ("test_queue", lambda: "test_body", None, TypeError, "Reply topic name is required. "),
            (
                None,
                None,
                None,
                TypeError,
                "Request queue name is required. Request body creator is required. Reply topic name is required. ",
            ),
            ("test_queue", lambda: "test_body", "test_topic", None, None),
        ],
    )
    def test_validate_params(
        self,
        request_queue_name,
        request_body_generator,
        reply_topic_name,
        expected_exception,
        expected_message,
    ):
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name=request_queue_name,
            request_body_generator=request_body_generator,
            reply_topic_name=reply_topic_name,
        )

        if expected_exception:
            with pytest.raises(expected_exception) as exc_info:
                operator._validate_params()
            assert str(exc_info.value) == expected_message
        else:
            operator._validate_params()  # Should not raise any exception

    @mock.patch("airflow.providers.microsoft.azure.operators.asb.ServiceBusAdministrationClient")
    def test_create_subscription(self, mock_admin_asb_conn):
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name="test_queue",
            request_body_generator=lambda: "test message body",
            reply_topic_name="reply-topic-name",
        )

        context = mock.MagicMock()
        context["task"] = mock.MagicMock()
        context["task"].task_id = 987
        operator._create_subscription(mock_admin_asb_conn, context)

        mock_admin_asb_conn.create_subscription.assert_called_once_with(
            topic_name="reply-topic-name",
            subscription_name=operator.subscription_name,
            default_message_time_to_live="PT1H",  # 1 hour
            dead_lettering_on_message_expiration=True,
            dead_lettering_on_filter_evaluation_exceptions=True,
            enable_batched_operations=False,
            user_metadata=f"Subscription for reply to {operator.reply_correlation_id} for task ID {context['task'].task_id}",
            auto_delete_on_idle="PT6H",  # 6 hours
        )

    @mock.patch("airflow.providers.microsoft.azure.operators.asb.ServiceBusAdministrationClient")
    def test_create_subscription_already_exists(self, mock_admin_asb_conn):
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name="test_queue",
            request_body_generator=lambda: "test_body",
            reply_topic_name="reply-topic-name",
        )

        context = mock.MagicMock()
        context["task"] = mock.MagicMock()
        context["task"].task_id = 234
        mock_admin_asb_conn.create_subscription.side_effect = ResourceExistsError

        with pytest.raises(ResourceExistsError):
            operator._create_subscription(mock_admin_asb_conn, context)

        mock_admin_asb_conn.create_subscription.assert_called_once_with(
            topic_name="reply-topic-name",
            subscription_name=operator.subscription_name,
            default_message_time_to_live="PT1H",  # 1 hour
            dead_lettering_on_message_expiration=True,
            dead_lettering_on_filter_evaluation_exceptions=True,
            enable_batched_operations=False,
            user_metadata=f"Subscription for reply to {operator.reply_correlation_id} for task ID {context['task'].task_id}",
            auto_delete_on_idle="PT6H",  # 6 hours
        )

    @mock.patch("airflow.providers.microsoft.azure.operators.asb.AdminClientHook")
    def test_create_reply_subscription_for_correlation_id(self, mock_admin_hook):
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name="test_queue",
            request_body_generator=lambda: "test_body",
            reply_topic_name="reply-topic-name",
        )

        context = mock.MagicMock()
        context["task"] = mock.MagicMock()
        context["task"].task_id = 345

        operator._create_reply_subscription_for_correlation_id(mock_admin_hook, context)

        mock_admin_hook.get_conn.return_value.__enter__.return_value.create_subscription.assert_called_once_with(
            topic_name="reply-topic-name",
            subscription_name=operator.subscription_name,
            default_message_time_to_live="PT1H",  # 1 hour
            dead_lettering_on_message_expiration=True,
            dead_lettering_on_filter_evaluation_exceptions=True,
            enable_batched_operations=False,
            user_metadata=f"Subscription for reply to {operator.reply_correlation_id} for task ID {context['task'].task_id}",
            auto_delete_on_idle="PT6H",  # 6 hours
        )

        mock_admin_hook.get_conn.return_value.__enter__.return_value.delete_rule.assert_called_once_with(
            "reply-topic-name", operator.subscription_name, "$Default"
        )

        mock_admin_hook.get_conn.return_value.__enter__.return_value.create_rule.assert_called_once_with(
            "reply-topic-name",
            operator.subscription_name,
            operator.subscription_name + operator.REPLY_RULE_SUFFIX,
            filter=mock.ANY,
        )

    @mock.patch("airflow.providers.microsoft.azure.operators.asb.AdminClientHook")
    def test_create_reply_subscription_for_correlation_id_subscription_exists(self, mock_admin_hook):
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name="test_queue",
            request_body_generator=lambda: "test_body",
            reply_topic_name="reply-topic-name",
        )

        context = mock.MagicMock()
        context["task"] = mock.MagicMock()
        context["task"].task_id = 987

        mock_admin_hook.get_conn.return_value.__enter__.return_value.create_subscription.side_effect = (
            ResourceExistsError
        )

        operator._create_reply_subscription_for_correlation_id(mock_admin_hook, context)

        mock_admin_hook.get_conn.return_value.__enter__.return_value.create_subscription.assert_called_once_with(
            topic_name="reply-topic-name",
            subscription_name=operator.subscription_name,
            default_message_time_to_live="PT1H",  # 1 hour
            dead_lettering_on_message_expiration=True,
            dead_lettering_on_filter_evaluation_exceptions=True,
            enable_batched_operations=False,
            user_metadata=f"Subscription for reply to {operator.reply_correlation_id} for task ID {context['task'].task_id}",
            auto_delete_on_idle="PT6H",  # 6 hours
        )

        mock_admin_hook.get_conn.return_value.__enter__.return_value.delete_rule.assert_not_called()
        mock_admin_hook.get_conn.return_value.__enter__.return_value.create_rule.assert_not_called()

    @mock.patch("airflow.providers.microsoft.azure.operators.asb.AdminClientHook")
    def test_create_reply_subscription_for_correlation_id_delete_rule_not_found(self, mock_admin_hook):
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name="test_queue",
            request_body_generator=lambda: "test_body",
            reply_topic_name="reply-topic-name",
        )

        context = mock.MagicMock()
        context["task"] = mock.MagicMock()
        context["task"].task_id = 789

        mock_admin_hook.get_conn.return_value.__enter__.return_value.delete_rule.side_effect = (
            ResourceNotFoundError
        )

        operator._create_reply_subscription_for_correlation_id(mock_admin_hook, context)

        mock_admin_hook.get_conn.return_value.__enter__.return_value.create_subscription.assert_called_once_with(
            topic_name="reply-topic-name",
            subscription_name=operator.subscription_name,
            default_message_time_to_live="PT1H",  # 1 hour
            dead_lettering_on_message_expiration=True,
            dead_lettering_on_filter_evaluation_exceptions=True,
            enable_batched_operations=False,
            user_metadata=f"Subscription for reply to {operator.reply_correlation_id} for task ID {context['task'].task_id}",
            auto_delete_on_idle="PT6H",  # 6 hours
        )

        mock_admin_hook.get_conn.return_value.__enter__.return_value.delete_rule.assert_called_once_with(
            "reply-topic-name", operator.subscription_name, "$Default"
        )

        mock_admin_hook.get_conn.return_value.__enter__.return_value.create_rule.assert_called_once_with(
            "reply-topic-name",
            operator.subscription_name,
            operator.subscription_name + operator.REPLY_RULE_SUFFIX,
            filter=mock.ANY,
        )

    @mock.patch("airflow.providers.microsoft.azure.operators.asb.MessageHook.get_conn")
    def test_send_request_message(self, mock_get_conn):
        TEST_MESSAGE_BODY = '{"fake-field": "fake-value"}'
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name="test_queue",
            request_body_generator=lambda context: TEST_MESSAGE_BODY,
            reply_topic_name="reply-topic-name",
        )

        context = mock.MagicMock()
        mock_service_bus_client = mock_get_conn.return_value.__enter__.return_value
        mock_sender = mock_service_bus_client.get_queue_sender.return_value.__enter__.return_value

        operator._send_request_message(MessageHook(), context)

        mock_service_bus_client.get_queue_sender.assert_called_once_with(queue_name="test_queue")
        mock_sender.send_messages.assert_called_once()
        sent_message = mock_sender.send_messages.call_args[0][0]
        assert str(sent_message) == TEST_MESSAGE_BODY
        assert sent_message.application_properties["reply_type"] == "topic"
        assert sent_message.message_id == operator.reply_correlation_id
        assert sent_message.reply_to == "reply-topic-name"

    @mock.patch("airflow.providers.microsoft.azure.operators.asb.AdminClientHook")
    @mock.patch("airflow.providers.microsoft.azure.operators.asb.MessageHook")
    def test_execute(self, mock_message_hook, mock_admin_hook):
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name="test_queue",
            request_body_generator=lambda context: "test_body",
            reply_topic_name="reply-topic-name",
        )

        context = mock.MagicMock()
        context["task"] = mock.MagicMock()
        context["task"].task_id = 837

        mock_message_hook_instance = mock_message_hook.return_value
        mock_admin_hook_instance = mock_admin_hook.return_value

        operator.execute(context)

        # Check if the reply subscription was created
        mock_admin_hook_instance.get_conn.return_value.__enter__.return_value.create_subscription.assert_called_once_with(
            topic_name="reply-topic-name",
            subscription_name=operator.subscription_name,
            default_message_time_to_live="PT1H",  # 1 hour
            dead_lettering_on_message_expiration=True,
            dead_lettering_on_filter_evaluation_exceptions=True,
            enable_batched_operations=False,
            user_metadata=f"Subscription for reply to {operator.reply_correlation_id} for task ID {context['task'].task_id}",
            auto_delete_on_idle="PT6H",  # 6 hours
        )

        # Check if the request message was sent
        mock_message_hook_instance.get_conn.return_value.__enter__.return_value.get_queue_sender.return_value.__enter__.return_value.send_messages.assert_called_once_with(
            mock.ANY, timeout=60
        )

        # Check if the reply message was received
        mock_message_hook_instance.receive_subscription_message.assert_called_once_with(
            "reply-topic-name",
            operator.subscription_name,
            context,
            max_message_count=1,
            max_wait_time=60,
            message_callback=None,
        )

        # Check if the reply subscription was removed
        mock_admin_hook_instance.delete_subscription.assert_called_once_with(
            operator.subscription_name, operator.reply_topic_name
        )

    @mock.patch("airflow.providers.microsoft.azure.operators.asb.AdminClientHook")
    @mock.patch("airflow.providers.microsoft.azure.operators.asb.MessageHook")
    def test_execute_with_exception(self, mock_message_hook, mock_admin_hook):
        operator = AzureServiceBusRequestReplyOperator(
            task_id="test_task",
            request_queue_name="test_queue",
            request_body_generator=lambda context: "test_body",
            reply_topic_name="reply-topic-name",
        )

        context = mock.MagicMock()
        context["task"] = mock.MagicMock()
        context["task"].task_id = 123

        mock_message_hook_instance = mock_message_hook.return_value
        mock_admin_hook_instance = mock_admin_hook.return_value

        # Simulate an exception during message sending
        mock_message_hook_instance.get_conn.return_value.__enter__.return_value.get_queue_sender.return_value.__enter__.return_value.send_messages.side_effect = Exception(
            "Test exception"
        )

        with pytest.raises(Exception, match="Test exception"):
            operator.execute(context)

        # Check if the reply subscription was still removed despite the exception
        mock_admin_hook_instance.delete_subscription.assert_called_once_with(
            operator.subscription_name, operator.reply_topic_name
        )
