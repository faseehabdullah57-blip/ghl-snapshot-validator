"""
GoHighLevel (GHL) API v2 Audit & Auto-Remediation Client.

Targets `https://services.leadconnectorhq.com` using Bearer token authentication,
the required `Version: 2021-07-28` header, and exponential backoff retry logic
on HTTP `429` (Rate Limit) and `5xx` responses. Also provides a built-in
multi-location `--mock` simulator with realistic configuration drift.
"""

from __future__ import annotations

import copy
import time
from typing import Any, Dict, List, Optional
import requests


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GHLAPIError(Exception):
    """Raised when a GoHighLevel API v2 request fails."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


DEFAULT_MOCK_SUBACCOUNT_STATE: Dict[str, Any] = {
    "customFields": [
        {
            "id": "cf_001",
            "name": "Lead Score",
            "fieldKey": "contact.lead_score",
            "dataType": "TEXT",  # Intentional drift: expected NUMERICAL
            "model": "contact",
        },
        {
            "id": "cf_002",
            "name": "Subscription Tier",
            "fieldKey": "contact.subscription_tier",
            "dataType": "SINGLE_OPTIONS",
            "model": "contact",
            # Intentional drift: missing "Enterprise" dropdown option
            "options": ["Starter", "Growth"],
        },
        {
            "id": "cf_003",
            "name": "Monthly Budget Range",
            "fieldKey": "contact.budget_range",
            "dataType": "SINGLE_OPTIONS",
            "model": "contact",
            "options": ["Under $2k/mo", "$2k - $5k/mo", "$5k+/mo"],
        },
        {
            "id": "cf_004",
            "name": "Account Manager Notes",
            "fieldKey": "contact.account_manager_notes",
            "dataType": "TEXT",
            "model": "contact",
        },
        # Intentional drift: "contact.onboarding_kickoff_date" is missing
        {
            "id": "cf_006",
            "name": "Projected MRR",
            "fieldKey": "opportunity.projected_mrr",
            "dataType": "NUMERICAL",
            "model": "opportunity",
        },
    ],
    "pipelines": [
        {
            "id": "pipe_sales_001",
            "name": "SaaS Sales & Acquisition Pipeline",
            "stages": [
                {"id": "stg_01", "name": "New Inbound Lead", "position": 0},
                {"id": "stg_02", "name": "Discovery Call Booked", "position": 1},
                # Intentional drift: Proposal Sent (2) and Demo Completed (3) are swapped
                {"id": "stg_04", "name": "Proposal Sent", "position": 2},
                {"id": "stg_03", "name": "Demo Completed", "position": 3},
                {"id": "stg_05", "name": "Closed Won", "position": 4},
            ],
        },
        {
            "id": "pipe_onboard_002",
            "name": "Client Onboarding & Fulfillment",
            "stages": [
                {"id": "stg_11", "name": "Welcome & Intake Form", "position": 0},
                {"id": "stg_12", "name": "Snapshot & Tech Setup", "position": 1},
                {"id": "stg_13", "name": "Automation QA & Testing", "position": 2},
                {"id": "stg_14", "name": "Go-Live & Handoff", "position": 3},
            ],
        },
    ],
    "tags": [
        {"id": "tag_01", "name": "Hot Lead"},
        {"id": "tag_02", "name": "Disqualified"},
        # Intentional drift: "Re-Engagement Needed" and "Onboarding Complete" are missing
        {"id": "tag_05", "name": "VIP Client"},
    ],
    "customValues": [
        {
            "id": "cv_01",
            "name": "Agency Calendar Link",
            "fieldKey": "custom_values.agency_calendar_link",
            "value": "",  # Intentional drift: Blank / empty custom value
        },
        {
            "id": "cv_02",
            "name": "Support Email",
            "fieldKey": "custom_values.support_email",
            "value": "support@agency-ops.io",
        },
        {
            "id": "cv_03",
            "name": "Twilio Default Sender Number",
            "fieldKey": "custom_values.twilio_default_sender",
            "value": "+18005550199",
        },
        # Intentional drift: "custom_values.stripe_billing_portal_url" is missing
    ],
    "workflows": [
        {
            "id": "wf_01",
            "name": "01. Speed to Lead - Instant SMS",
            "status": "published",
        },
        {
            "id": "wf_02",
            "name": "02. Appointment Reminder Sequence",
            "status": "draft",  # Intentional drift: stuck in draft instead of published
        },
        {
            "id": "wf_03",
            "name": "03. No-Show Re-Engagement Drip",
            "status": "published",
        },
        {
            "id": "wf_04",
            "name": "04. Post-Onboarding NPS & Review Request",
            "status": "published",
        },
    ],
}


COMPLIANT_MOCK_SUBACCOUNT_STATE: Dict[str, Any] = {
    "customFields": [
        {
            "id": "cf_001",
            "name": "Lead Score",
            "fieldKey": "contact.lead_score",
            "dataType": "NUMERICAL",
            "model": "contact",
        },
        {
            "id": "cf_002",
            "name": "Subscription Tier",
            "fieldKey": "contact.subscription_tier",
            "dataType": "SINGLE_OPTIONS",
            "model": "contact",
            "options": ["Starter", "Growth", "Enterprise"],
        },
        {
            "id": "cf_003",
            "name": "Monthly Budget Range",
            "fieldKey": "contact.budget_range",
            "dataType": "SINGLE_OPTIONS",
            "model": "contact",
            "options": ["Under $2k/mo", "$2k - $5k/mo", "$5k+/mo"],
        },
        {
            "id": "cf_004",
            "name": "Account Manager Notes",
            "fieldKey": "contact.account_manager_notes",
            "dataType": "TEXT",
            "model": "contact",
        },
        {
            "id": "cf_005",
            "name": "Onboarding Kickoff Date",
            "fieldKey": "contact.onboarding_kickoff_date",
            "dataType": "DATE",
            "model": "contact",
        },
        {
            "id": "cf_006",
            "name": "Projected MRR",
            "fieldKey": "opportunity.projected_mrr",
            "dataType": "NUMERICAL",
            "model": "opportunity",
        },
    ],
    "pipelines": [
        {
            "id": "pipe_sales_001",
            "name": "SaaS Sales & Acquisition Pipeline",
            "stages": [
                {"id": "stg_01", "name": "New Inbound Lead", "position": 0},
                {"id": "stg_02", "name": "Discovery Call Booked", "position": 1},
                {"id": "stg_03", "name": "Demo Completed", "position": 2},
                {"id": "stg_04", "name": "Proposal Sent", "position": 3},
                {"id": "stg_05", "name": "Closed Won", "position": 4},
            ],
        },
        {
            "id": "pipe_onboard_002",
            "name": "Client Onboarding & Fulfillment",
            "stages": [
                {"id": "stg_11", "name": "Welcome & Intake Form", "position": 0},
                {"id": "stg_12", "name": "Snapshot & Tech Setup", "position": 1},
                {"id": "stg_13", "name": "Automation QA & Testing", "position": 2},
                {"id": "stg_14", "name": "Go-Live & Handoff", "position": 3},
            ],
        },
    ],
    "tags": [
        {"id": "tag_01", "name": "Hot Lead"},
        {"id": "tag_02", "name": "Disqualified"},
        {"id": "tag_03", "name": "Re-Engagement Needed"},
        {"id": "tag_04", "name": "Onboarding Complete"},
        {"id": "tag_05", "name": "VIP Client"},
    ],
    "customValues": [
        {
            "id": "cv_01",
            "name": "Agency Calendar Link",
            "fieldKey": "custom_values.agency_calendar_link",
            "value": "https://msgsndr.com/widget/booking/agency-discovery",
        },
        {
            "id": "cv_02",
            "name": "Support Email",
            "fieldKey": "custom_values.support_email",
            "value": "support@agency-ops.io",
        },
        {
            "id": "cv_03",
            "name": "Twilio Default Sender Number",
            "fieldKey": "custom_values.twilio_default_sender",
            "value": "+18005550199",
        },
        {
            "id": "cv_04",
            "name": "Stripe Billing Portal URL",
            "fieldKey": "custom_values.stripe_billing_portal_url",
            "value": "https://billing.agency-ops.io/portal",
        },
    ],
    "workflows": [
        {
            "id": "wf_01",
            "name": "01. Speed to Lead - Instant SMS",
            "status": "published",
        },
        {
            "id": "wf_02",
            "name": "02. Appointment Reminder Sequence",
            "status": "published",
        },
        {
            "id": "wf_03",
            "name": "03. No-Show Re-Engagement Drip",
            "status": "published",
        },
        {
            "id": "wf_04",
            "name": "04. Post-Onboarding NPS & Review Request",
            "status": "published",
        },
    ],
}


def _build_fixable_only_mock_state() -> Dict[str, Any]:
    """Build a mock sub-account state with only auto-fixable missing resources."""
    state = copy.deepcopy(COMPLIANT_MOCK_SUBACCOUNT_STATE)
    # Remove 1 tag and 1 custom value so --auto-fix brings it from 92.6% to 100%
    state["tags"] = [t for t in state["tags"] if t["name"] != "Onboarding Complete"]
    state["customValues"] = [
        cv
        for cv in state["customValues"]
        if cv["fieldKey"] != "custom_values.stripe_billing_portal_url"
    ]
    return state


MOCK_MULTI_LOCATION_STATES: Dict[str, Dict[str, Any]] = {
    "loc_apex_dental_001": COMPLIANT_MOCK_SUBACCOUNT_STATE,
    "loc_elevate_medspa_002": _build_fixable_only_mock_state(),
    "loc_summit_roofing_003": DEFAULT_MOCK_SUBACCOUNT_STATE,
}


class GHLAuditClient:
    """
    HTTP client for auditing and auto-remediating GoHighLevel sub-account resources
    via the LeadConnector / GHL API v2 (`https://services.leadconnectorhq.com`).
    """

    BASE_URL = "https://services.leadconnectorhq.com"
    API_VERSION = "2021-07-28"

    def __init__(
        self,
        api_key: str = "",
        location_id: str = "",
        base_url: str = BASE_URL,
        timeout: int = 15,
        max_retries: int = 3,
        backoff_factor: float = 0.25,
        mock: bool = False,
        mock_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.api_key = api_key
        self.location_id = location_id or ("mock-location-001" if mock else "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.mock = mock

        if mock_state is not None:
            initial_state = mock_state
        elif self.location_id in MOCK_MULTI_LOCATION_STATES:
            initial_state = MOCK_MULTI_LOCATION_STATES[self.location_id]
        else:
            initial_state = DEFAULT_MOCK_SUBACCOUNT_STATE

        self._mock_state: Dict[str, Any] = copy.deepcopy(initial_state)
        self.remediation_log: List[Dict[str, Any]] = []

    @property
    def headers(self) -> Dict[str, str]:
        """Standard GHL API v2 headers with Bearer token and Version 2021-07-28."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Version": self.API_VERSION,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a GET or POST request against GHL API v2 with automatic
        exponential backoff on HTTP 429 (Rate Limit) and 5xx server errors.
        """
        url = f"{self.base_url}{endpoint}"
        last_response: Optional[requests.Response] = None

        for attempt in range(self.max_retries + 1):
            if method.upper() == "GET":
                response = requests.get(
                    url, headers=self.headers, timeout=self.timeout
                )
            else:
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=json_payload,
                    timeout=self.timeout,
                )

            last_response = response
            if (
                response.status_code in RETRYABLE_STATUS_CODES
                and attempt < self.max_retries
            ):
                sleep_seconds = self.backoff_factor * (2**attempt)
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
                continue
            break

        assert last_response is not None
        return self._handle_response(last_response, endpoint)

    def _handle_response(
        self, response: requests.Response, endpoint: str
    ) -> Dict[str, Any]:
        """Validate HTTP status code and parse JSON payload."""
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body: Any = None
            try:
                body = response.json()
            except ValueError:
                body = response.text
            raise GHLAPIError(
                f"GHL API v2 error on {endpoint} (HTTP {response.status_code}): {body}",
                status_code=response.status_code,
                response_body=body,
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise GHLAPIError(
                f"Invalid JSON returned from {endpoint}",
                status_code=response.status_code,
                response_body=response.text,
            ) from exc

    # -------------------------------------------------------------------------
    # GET Audit Endpoints
    # -------------------------------------------------------------------------

    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """
        Fetch custom fields for the sub-account.
        Endpoint: GET /locations/{locationId}/customFields
        """
        if self.mock:
            return copy.deepcopy(self._mock_state.get("customFields", []))

        endpoint = f"/locations/{self.location_id}/customFields"
        data = self._request_with_retry("GET", endpoint)
        return data.get("customFields", [])

    def get_pipelines(self) -> List[Dict[str, Any]]:
        """
        Fetch opportunity pipelines and ordered stages for the sub-account.
        Endpoint: GET /opportunities/pipelines?locationId={locationId}
        """
        if self.mock:
            return copy.deepcopy(self._mock_state.get("pipelines", []))

        endpoint = f"/opportunities/pipelines?locationId={self.location_id}"
        data = self._request_with_retry("GET", endpoint)
        return data.get("pipelines", [])

    def get_tags(self) -> List[Dict[str, Any]]:
        """
        Fetch location tags for the sub-account.
        Endpoint: GET /locations/{locationId}/tags
        """
        if self.mock:
            return copy.deepcopy(self._mock_state.get("tags", []))

        endpoint = f"/locations/{self.location_id}/tags"
        data = self._request_with_retry("GET", endpoint)
        return data.get("tags", [])

    def get_custom_values(self) -> List[Dict[str, Any]]:
        """
        Fetch location custom values for the sub-account.
        Endpoint: GET /locations/{locationId}/customValues
        """
        if self.mock:
            return copy.deepcopy(self._mock_state.get("customValues", []))

        endpoint = f"/locations/{self.location_id}/customValues"
        data = self._request_with_retry("GET", endpoint)
        return data.get("customValues", [])

    def get_workflows(self) -> List[Dict[str, Any]]:
        """
        Fetch workflows and their publication status (`published` vs `draft`).
        Endpoint: GET /workflows/?locationId={locationId}
        """
        if self.mock:
            return copy.deepcopy(self._mock_state.get("workflows", []))

        endpoint = f"/workflows/?locationId={self.location_id}"
        data = self._request_with_retry("GET", endpoint)
        return data.get("workflows", [])

    def fetch_all_snapshot_data(self) -> Dict[str, Any]:
        """Fetch all audited resource categories from the sub-account."""
        return {
            "customFields": self.get_custom_fields(),
            "pipelines": self.get_pipelines(),
            "tags": self.get_tags(),
            "customValues": self.get_custom_values(),
            "workflows": self.get_workflows(),
        }

    # -------------------------------------------------------------------------
    # POST Auto-Fix / Remediation Endpoints
    # -------------------------------------------------------------------------

    def create_tag(self, name: str) -> Dict[str, Any]:
        """
        Create a missing tag in the sub-account.
        Endpoint: POST /locations/{locationId}/tags
        """
        endpoint = f"/locations/{self.location_id}/tags"
        payload = {"name": name}

        if self.mock:
            created = {
                "id": f"mock_tag_{len(self._mock_state.get('tags', [])) + 1}",
                "name": name,
            }
            self._mock_state.setdefault("tags", []).append(created)
            self.remediation_log.append({"endpoint": endpoint, "payload": payload})
            return {"tag": created}

        data = self._request_with_retry("POST", endpoint, json_payload=payload)
        self.remediation_log.append({"endpoint": endpoint, "payload": payload})
        return data

    def create_custom_field(
        self,
        field_data: Optional[Dict[str, Any]] = None,
        *,
        name: Optional[str] = None,
        dataType: Optional[str] = None,
        model: str = "contact",
        fieldKey: Optional[str] = None,
        options: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a missing custom field in the sub-account.
        Endpoint: POST /locations/{locationId}/customFields
        """
        source = dict(field_data or {})
        if name is not None:
            source["name"] = name
        if dataType is not None:
            source["dataType"] = dataType
        if "model" not in source:
            source["model"] = model
        if fieldKey is not None:
            source["fieldKey"] = fieldKey
        if options is not None:
            source["options"] = options

        payload: Dict[str, Any] = {
            "name": source["name"],
            "dataType": source["dataType"],
            "model": source.get("model", "contact"),
        }
        if "fieldKey" in source and source["fieldKey"]:
            payload["fieldKey"] = source["fieldKey"]
        if "options" in source and source["options"]:
            payload["options"] = source["options"]

        endpoint = f"/locations/{self.location_id}/customFields"

        if self.mock:
            created = {
                "id": f"mock_cf_{len(self._mock_state.get('customFields', [])) + 1}",
                **payload,
            }
            self._mock_state.setdefault("customFields", []).append(created)
            self.remediation_log.append({"endpoint": endpoint, "payload": payload})
            return {"customField": created}

        data = self._request_with_retry("POST", endpoint, json_payload=payload)
        self.remediation_log.append({"endpoint": endpoint, "payload": payload})
        return data

    def create_custom_value(
        self,
        value_data: Optional[Dict[str, Any]] = None,
        *,
        name: Optional[str] = None,
        fieldKey: Optional[str] = None,
        value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a missing custom value in the sub-account.
        Endpoint: POST /locations/{locationId}/customValues
        """
        source = dict(value_data or {})
        if name is not None:
            source["name"] = name
        if fieldKey is not None:
            source["fieldKey"] = fieldKey
        if value is not None:
            source["value"] = value

        payload: Dict[str, Any] = {
            "name": source["name"],
            "value": source.get("value", "https://agency-ops.io/configured"),
        }
        if "fieldKey" in source and source["fieldKey"]:
            payload["fieldKey"] = source["fieldKey"]

        endpoint = f"/locations/{self.location_id}/customValues"

        if self.mock:
            created = {
                "id": f"mock_cv_{len(self._mock_state.get('customValues', [])) + 1}",
                **payload,
            }
            self._mock_state.setdefault("customValues", []).append(created)
            self.remediation_log.append({"endpoint": endpoint, "payload": payload})
            return {"customValue": created}

        data = self._request_with_retry("POST", endpoint, json_payload=payload)
        self.remediation_log.append({"endpoint": endpoint, "payload": payload})
        return data
