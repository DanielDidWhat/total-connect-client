"""Test total_connect_client request()."""

import unittest
from unittest.mock import patch

import pytest
from total_connect_client.client import TotalConnectClient
from total_connect_client.exceptions import TotalConnectError, AuthenticationError
from const import (
    LOCATION_INFO_BASIC_NORMAL,
    RESPONSE_ARMED_AWAY,
    RESPONSE_AUTHENTICATE,
    RESPONSE_BAD_USER_OR_PASSWORD,
    RESPONSE_CONNECTION_ERROR,
    RESPONSE_DISARMED,
    RESPONSE_FAILED_TO_CONNECT,
    RESPONSE_GET_ZONE_DETAILS_SUCCESS,
    RESPONSE_INVALID_SESSION,
    RESPONSE_PARTITION_DETAILS,
    RESPONSE_SESSION_INITIATED,
    RESPONSE_UNKNOWN,
)


class FakeResponse:
    """Fake response from zeep."""

    def __init__(self, code, data):
        """Initialize."""
        self.ResultCode = code
        self.ResultData = data


class TestTotalConnectClient(unittest.TestCase):
    """Test TotalConnectClient request()."""

    def setUp(self):
        """Test setup."""
        self.client = None
        self.location_id = LOCATION_INFO_BASIC_NORMAL["LocationID"]

    def tearDown(self):
        """Test cleanup."""
        self.client = None

    def tests_request_init(self):
        """Test normal init sequence with no problems."""
        eval_responses = [
            FakeResponse(
                RESPONSE_AUTHENTICATE["ResultCode"], "Authentication Succeess."
            ),
            FakeResponse(RESPONSE_PARTITION_DETAILS["ResultCode"], "Partition Success"),
            FakeResponse(
                RESPONSE_GET_ZONE_DETAILS_SUCCESS["ResultCode"], "Zone Details Success"
            ),
            FakeResponse(RESPONSE_DISARMED["ResultCode"], "Response Disarmed"),
        ]
        serialize_responses = [
            RESPONSE_AUTHENTICATE,
            RESPONSE_PARTITION_DETAILS,
            RESPONSE_GET_ZONE_DETAILS_SUCCESS,
            RESPONSE_DISARMED,
        ]

        with patch(
            "zeep.helpers.serialize_object", side_effect=serialize_responses
        ), patch(
            "builtins.eval", side_effect=eval_responses
        ) as mock_request:
            client = TotalConnectClient("username", "password", usercodes=None)
            assert mock_request.call_count == 1
            if client.locations:  # force client to fetch them
                pass
            assert mock_request.call_count == 4
            assert client.is_valid_credentials() is True
            assert client.is_logged_in() is True

    def tests_request_init_bad_user_or_password(self):
        """Test init sequence with no a bad password."""
        eval_responses = [
            FakeResponse(
                RESPONSE_BAD_USER_OR_PASSWORD["ResultCode"], "Response Disarmed"
            ),
        ]
        serialize_responses = [
            RESPONSE_BAD_USER_OR_PASSWORD,
        ]

        with patch(
            "zeep.helpers.serialize_object", side_effect=serialize_responses
        ), patch(
            "builtins.eval", side_effect=eval_responses
        ) as mock_request:
            with pytest.raises(AuthenticationError):
                TotalConnectClient("username", "password", usercodes=None)
            assert mock_request.call_count == 1

    def tests_request_init_failed_to_connect(self):
        """Test init sequence when fails to connect."""
        eval_responses = []
        serialize_responses = []
        for x in range(TotalConnectClient.MAX_RETRY_ATTEMPTS):
            eval_responses.append(
                FakeResponse(
                    RESPONSE_FAILED_TO_CONNECT["ResultCode"], "Response Disarmed"
                )
            )
            serialize_responses.append(RESPONSE_FAILED_TO_CONNECT)

        with patch(
            "zeep.helpers.serialize_object", side_effect=serialize_responses
        ), patch(
            "time.sleep", autospec=True
        ), patch(
            "builtins.eval", side_effect=eval_responses
        ) as mock_request, pytest.raises(
            Exception
        ) as e:
            client = TotalConnectClient(
                "username", "password", usercodes=None, retry_delay=0
            )
            assert mock_request.call_count == TotalConnectClient.MAX_RETRY_ATTEMPTS
            assert client.is_valid_credentials() is False
            assert client.is_logged_in() is False
            assert (
                str(e.value)
                == "total-connect-client could not execute request.  Maximum attempts tried."
            )

    def tests_request_connection_error(self):
        """Test a connection error."""
        eval_responses = []
        serialize_responses = []
        for x in range(TotalConnectClient.MAX_RETRY_ATTEMPTS):
            eval_responses.append(
                FakeResponse(
                    RESPONSE_CONNECTION_ERROR["ResultCode"], "Response Disarmed"
                )
            )
            serialize_responses.append(RESPONSE_CONNECTION_ERROR)

        with patch(
            "zeep.helpers.serialize_object", side_effect=serialize_responses
        ), patch(
            "time.sleep", autospec=True
        ), patch(
            "builtins.eval", side_effect=eval_responses
        ) as mock_request, pytest.raises(
            Exception
        ) as e:
            client = TotalConnectClient("username", "password", usercodes=None, retry_delay=0)
            assert mock_request.call_count == TotalConnectClient.MAX_RETRY_ATTEMPTS
            assert client.is_valid_credentials() is False
            assert client.is_logged_in() is False
            assert (
                str(e.value)
                == "total-connect-client could not execute request.  Maximum attempts tried."
            )

    def tests_request_invalid_session(self):
        """Test an invalid session, which is when the session times out."""
        # First three responses set up 'normal' session
        # Call to client.arm_away() will first get an invalid session,
        # which will trigger client.authenticate() before completing the arm_away()
        eval_responses = [
            FakeResponse(
                RESPONSE_AUTHENTICATE["ResultCode"], "Authentication Succeess."
            ),
            FakeResponse(RESPONSE_PARTITION_DETAILS["ResultCode"], "Partition Success"),
            FakeResponse(
                RESPONSE_GET_ZONE_DETAILS_SUCCESS["ResultCode"], "Zone Details Success"
            ),
            FakeResponse(RESPONSE_DISARMED["ResultCode"], "Response Disarmed"),
            FakeResponse(
                RESPONSE_INVALID_SESSION["ResultCode"], "Response Invalid Session"
            ),
            FakeResponse(
                RESPONSE_SESSION_INITIATED["ResultCode"], "Session initiated."
            ),
            FakeResponse(RESPONSE_ARMED_AWAY["ResultCode"], "Response armed"),
        ]
        # invalid_session responses don't get serialized
        serialize_responses = [
            RESPONSE_AUTHENTICATE,
            RESPONSE_PARTITION_DETAILS,
            RESPONSE_GET_ZONE_DETAILS_SUCCESS,
            RESPONSE_DISARMED,
            RESPONSE_SESSION_INITIATED,
            RESPONSE_ARMED_AWAY,
        ]

        with patch(
            "zeep.helpers.serialize_object", side_effect=serialize_responses
        ), patch(
            "builtins.eval", side_effect=eval_responses
        ) as mock_request:
            client = TotalConnectClient("username", "password", usercodes=None)
            assert mock_request.call_count == 1
            if client.locations:  # force client to fetch them
                pass
            assert mock_request.call_count == 4
            assert client.is_valid_credentials() is True
            assert client.is_logged_in() is True

            client.arm_away(self.location_id)
            assert mock_request.call_count == 5

    def tests_request_unknown_result_code(self):
        """Test an unknown result code."""
        eval_responses = [
            FakeResponse(RESPONSE_UNKNOWN["ResultCode"], "unknown code."),
        ]
        serialize_responses = [
            RESPONSE_UNKNOWN,
        ]

        with patch(
            "zeep.helpers.serialize_object", side_effect=serialize_responses
        ), patch(
            "builtins.eval", side_effect=eval_responses
        ) as mock_request:
            with pytest.raises(TotalConnectError):
                TotalConnectClient("username", "password", usercodes=None)
            assert mock_request.call_count == 1
