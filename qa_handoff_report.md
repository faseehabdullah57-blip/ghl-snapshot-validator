# GoHighLevel Snapshot QA & Onboarding Readiness Report

- **Generated At**: `2026-11-13 06:29:24 UTC`
- **Master Blueprint**: `master_agency_blueprint.json`
- **Execution Mode**: `Mock Simulation`
- **Auto-Fix Remediation**: `Enabled`
- **Overall Verdict**: **FAIL - Configuration Drift Requires Attention**

---

## Agency Health Scoreboard

| Location | Readiness % | Passed | Failed | Auto-Fixed | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Apex Dental Studio (Production) (`loc_apex_dental_001`) | **100.0%** | 30 | 0 | 0 | **PASS** |
| Elevate MedSpa & Wellness (Onboarding) (`loc_elevate_medspa_002`) | **100.0%** | 28 | 0 | 2 | **PASS** |
| Summit Roofing Group (Staging) (`loc_summit_roofing_003`) | **80.0%** | 20 | 6 | 4 | **FAIL** |

---

## Sub-Account Audit Details: Apex Dental Studio (Production) (loc_apex_dental_001)

**Readiness**: `100.0%` | **Passed**: `30` | **Auto-Fixed**: `0` | **Failed**: `0`

| Resource Type | Resource Name | Expected | Actual | Status |
| :--- | :--- | :--- | :--- | :---: |
| Custom Field | Lead Score (contact.lead_score) | `dataType=NUMERICAL, model=contact` | `dataType=NUMERICAL, model=contact` | **PASS** |
| Custom Field | Subscription Tier (contact.subscription_tier) | `dataType=SINGLE_OPTIONS, model=contact, options=['Starter', 'Growth', 'Enterprise']` | `dataType=SINGLE_OPTIONS, model=contact, options=['Starter', 'Growth', 'Enterprise']` | **PASS** |
| Custom Field | Monthly Budget Range (contact.budget_range) | `dataType=SINGLE_OPTIONS, model=contact, options=['Under $2k/mo', '$2k - $5k/mo', '$5k+/mo']` | `dataType=SINGLE_OPTIONS, model=contact, options=['Under $2k/mo', '$2k - $5k/mo', '$5k+/mo']` | **PASS** |
| Custom Field | Account Manager Notes (contact.account_manager_notes) | `dataType=TEXT, model=contact` | `dataType=TEXT, model=contact` | **PASS** |
| Custom Field | Onboarding Kickoff Date (contact.onboarding_kickoff_date) | `dataType=DATE, model=contact` | `dataType=DATE, model=contact` | **PASS** |
| Custom Field | Projected MRR (opportunity.projected_mrr) | `dataType=NUMERICAL, model=opportunity` | `dataType=NUMERICAL, model=opportunity` | **PASS** |
| Pipeline | SaaS Sales & Acquisition Pipeline | `Present (5 stages)` | `Present (5 stages)` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> New Inbound Lead | `position=0` | `position=0` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Discovery Call Booked | `position=1` | `position=1` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Demo Completed | `position=2` | `position=2` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Proposal Sent | `position=3` | `position=3` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Closed Won | `position=4` | `position=4` | **PASS** |
| Pipeline | Client Onboarding & Fulfillment | `Present (4 stages)` | `Present (4 stages)` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Welcome & Intake Form | `position=0` | `position=0` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Snapshot & Tech Setup | `position=1` | `position=1` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Automation QA & Testing | `position=2` | `position=2` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Go-Live & Handoff | `position=3` | `position=3` | **PASS** |
| Tag | Hot Lead | `Present` | `Present` | **PASS** |
| Tag | Disqualified | `Present` | `Present` | **PASS** |
| Tag | Re-Engagement Needed | `Present` | `Present` | **PASS** |
| Tag | Onboarding Complete | `Present` | `Present` | **PASS** |
| Tag | VIP Client | `Present` | `Present` | **PASS** |
| Custom Value | Agency Calendar Link (custom_values.agency_calendar_link) | `fieldKey=custom_values.agency_calendar_link (non-empty)` | `fieldKey=custom_values.agency_calendar_link, value="https://msgsndr.com/widget/booking/agency-discovery"` | **PASS** |
| Custom Value | Support Email (custom_values.support_email) | `fieldKey=custom_values.support_email (non-empty)` | `fieldKey=custom_values.support_email, value="support@agency-ops.io"` | **PASS** |
| Custom Value | Twilio Default Sender Number (custom_values.twilio_default_sender) | `fieldKey=custom_values.twilio_default_sender (non-empty)` | `fieldKey=custom_values.twilio_default_sender, value="+18005550199"` | **PASS** |
| Custom Value | Stripe Billing Portal URL (custom_values.stripe_billing_portal_url) | `fieldKey=custom_values.stripe_billing_portal_url (non-empty)` | `fieldKey=custom_values.stripe_billing_portal_url, value="https://billing.agency-ops.io/portal"` | **PASS** |
| Workflow | 01. Speed to Lead - Instant SMS | `status=published` | `status=published` | **PASS** |
| Workflow | 02. Appointment Reminder Sequence | `status=published` | `status=published` | **PASS** |
| Workflow | 03. No-Show Re-Engagement Drip | `status=published` | `status=published` | **PASS** |
| Workflow | 04. Post-Onboarding NPS & Review Request | `status=published` | `status=published` | **PASS** |

## Sub-Account Audit Details: Elevate MedSpa & Wellness (Onboarding) (loc_elevate_medspa_002)

**Readiness**: `100.0%` | **Passed**: `28` | **Auto-Fixed**: `2` | **Failed**: `0`

| Resource Type | Resource Name | Expected | Actual | Status |
| :--- | :--- | :--- | :--- | :---: |
| Custom Field | Lead Score (contact.lead_score) | `dataType=NUMERICAL, model=contact` | `dataType=NUMERICAL, model=contact` | **PASS** |
| Custom Field | Subscription Tier (contact.subscription_tier) | `dataType=SINGLE_OPTIONS, model=contact, options=['Starter', 'Growth', 'Enterprise']` | `dataType=SINGLE_OPTIONS, model=contact, options=['Starter', 'Growth', 'Enterprise']` | **PASS** |
| Custom Field | Monthly Budget Range (contact.budget_range) | `dataType=SINGLE_OPTIONS, model=contact, options=['Under $2k/mo', '$2k - $5k/mo', '$5k+/mo']` | `dataType=SINGLE_OPTIONS, model=contact, options=['Under $2k/mo', '$2k - $5k/mo', '$5k+/mo']` | **PASS** |
| Custom Field | Account Manager Notes (contact.account_manager_notes) | `dataType=TEXT, model=contact` | `dataType=TEXT, model=contact` | **PASS** |
| Custom Field | Onboarding Kickoff Date (contact.onboarding_kickoff_date) | `dataType=DATE, model=contact` | `dataType=DATE, model=contact` | **PASS** |
| Custom Field | Projected MRR (opportunity.projected_mrr) | `dataType=NUMERICAL, model=opportunity` | `dataType=NUMERICAL, model=opportunity` | **PASS** |
| Pipeline | SaaS Sales & Acquisition Pipeline | `Present (5 stages)` | `Present (5 stages)` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> New Inbound Lead | `position=0` | `position=0` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Discovery Call Booked | `position=1` | `position=1` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Demo Completed | `position=2` | `position=2` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Proposal Sent | `position=3` | `position=3` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Closed Won | `position=4` | `position=4` | **PASS** |
| Pipeline | Client Onboarding & Fulfillment | `Present (4 stages)` | `Present (4 stages)` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Welcome & Intake Form | `position=0` | `position=0` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Snapshot & Tech Setup | `position=1` | `position=1` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Automation QA & Testing | `position=2` | `position=2` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Go-Live & Handoff | `position=3` | `position=3` | **PASS** |
| Tag | Hot Lead | `Present` | `Present` | **PASS** |
| Tag | Disqualified | `Present` | `Present` | **PASS** |
| Tag | Re-Engagement Needed | `Present` | `Present` | **PASS** |
| Tag | Onboarding Complete | `Present` | `Created via Auto-Fix (POST /tags)` | **FIXED** |
| Tag | VIP Client | `Present` | `Present` | **PASS** |
| Custom Value | Agency Calendar Link (custom_values.agency_calendar_link) | `fieldKey=custom_values.agency_calendar_link (non-empty)` | `fieldKey=custom_values.agency_calendar_link, value="https://msgsndr.com/widget/booking/agency-discovery"` | **PASS** |
| Custom Value | Support Email (custom_values.support_email) | `fieldKey=custom_values.support_email (non-empty)` | `fieldKey=custom_values.support_email, value="support@agency-ops.io"` | **PASS** |
| Custom Value | Twilio Default Sender Number (custom_values.twilio_default_sender) | `fieldKey=custom_values.twilio_default_sender (non-empty)` | `fieldKey=custom_values.twilio_default_sender, value="+18005550199"` | **PASS** |
| Custom Value | Stripe Billing Portal URL (custom_values.stripe_billing_portal_url) | `fieldKey=custom_values.stripe_billing_portal_url (non-empty)` | `Created via Auto-Fix (POST /customValues)` | **FIXED** |
| Workflow | 01. Speed to Lead - Instant SMS | `status=published` | `status=published` | **PASS** |
| Workflow | 02. Appointment Reminder Sequence | `status=published` | `status=published` | **PASS** |
| Workflow | 03. No-Show Re-Engagement Drip | `status=published` | `status=published` | **PASS** |
| Workflow | 04. Post-Onboarding NPS & Review Request | `status=published` | `status=published` | **PASS** |

## Sub-Account Audit Details: Summit Roofing Group (Staging) (loc_summit_roofing_003)

**Readiness**: `80.0%` | **Passed**: `20` | **Auto-Fixed**: `4` | **Failed**: `6`

| Resource Type | Resource Name | Expected | Actual | Status |
| :--- | :--- | :--- | :--- | :---: |
| Custom Field | Lead Score (contact.lead_score) | `dataType=NUMERICAL, model=contact` | `dataType=TEXT, model=contact [TYPE MISMATCH]` | **FAIL** |
| Custom Field | Subscription Tier (contact.subscription_tier) | `dataType=SINGLE_OPTIONS, model=contact, options=['Starter', 'Growth', 'Enterprise']` | `options=['Starter', 'Growth'] [MISSING OPTIONS: ['Enterprise']]` | **FAIL** |
| Custom Field | Monthly Budget Range (contact.budget_range) | `dataType=SINGLE_OPTIONS, model=contact, options=['Under $2k/mo', '$2k - $5k/mo', '$5k+/mo']` | `dataType=SINGLE_OPTIONS, model=contact, options=['Under $2k/mo', '$2k - $5k/mo', '$5k+/mo']` | **PASS** |
| Custom Field | Account Manager Notes (contact.account_manager_notes) | `dataType=TEXT, model=contact` | `dataType=TEXT, model=contact` | **PASS** |
| Custom Field | Onboarding Kickoff Date (contact.onboarding_kickoff_date) | `dataType=DATE, model=contact` | `Created via Auto-Fix (DATE, contact)` | **FIXED** |
| Custom Field | Projected MRR (opportunity.projected_mrr) | `dataType=NUMERICAL, model=opportunity` | `dataType=NUMERICAL, model=opportunity` | **PASS** |
| Pipeline | SaaS Sales & Acquisition Pipeline | `Present (5 stages)` | `Present (5 stages)` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> New Inbound Lead | `position=0` | `position=0` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Discovery Call Booked | `position=1` | `position=1` | **PASS** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Demo Completed | `position=2` | `position=3 [OUT OF ORDER]` | **FAIL** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Proposal Sent | `position=3` | `position=2 [OUT OF ORDER]` | **FAIL** |
| Pipeline Stage | SaaS Sales & Acquisition Pipeline -> Closed Won | `position=4` | `position=4` | **PASS** |
| Pipeline | Client Onboarding & Fulfillment | `Present (4 stages)` | `Present (4 stages)` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Welcome & Intake Form | `position=0` | `position=0` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Snapshot & Tech Setup | `position=1` | `position=1` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Automation QA & Testing | `position=2` | `position=2` | **PASS** |
| Pipeline Stage | Client Onboarding & Fulfillment -> Go-Live & Handoff | `position=3` | `position=3` | **PASS** |
| Tag | Hot Lead | `Present` | `Present` | **PASS** |
| Tag | Disqualified | `Present` | `Present` | **PASS** |
| Tag | Re-Engagement Needed | `Present` | `Created via Auto-Fix (POST /tags)` | **FIXED** |
| Tag | Onboarding Complete | `Present` | `Created via Auto-Fix (POST /tags)` | **FIXED** |
| Tag | VIP Client | `Present` | `Present` | **PASS** |
| Custom Value | Agency Calendar Link (custom_values.agency_calendar_link) | `fieldKey=custom_values.agency_calendar_link (non-empty)` | `value="" [BLANK / EMPTY]` | **FAIL** |
| Custom Value | Support Email (custom_values.support_email) | `fieldKey=custom_values.support_email (non-empty)` | `fieldKey=custom_values.support_email, value="support@agency-ops.io"` | **PASS** |
| Custom Value | Twilio Default Sender Number (custom_values.twilio_default_sender) | `fieldKey=custom_values.twilio_default_sender (non-empty)` | `fieldKey=custom_values.twilio_default_sender, value="+18005550199"` | **PASS** |
| Custom Value | Stripe Billing Portal URL (custom_values.stripe_billing_portal_url) | `fieldKey=custom_values.stripe_billing_portal_url (non-empty)` | `Created via Auto-Fix (POST /customValues)` | **FIXED** |
| Workflow | 01. Speed to Lead - Instant SMS | `status=published` | `status=published` | **PASS** |
| Workflow | 02. Appointment Reminder Sequence | `status=published` | `status=draft [DRAFT / UNPUBLISHED]` | **FAIL** |
| Workflow | 03. No-Show Re-Engagement Drip | `status=published` | `status=published` | **PASS** |
| Workflow | 04. Post-Onboarding NPS & Review Request | `status=published` | `status=published` | **PASS** |
