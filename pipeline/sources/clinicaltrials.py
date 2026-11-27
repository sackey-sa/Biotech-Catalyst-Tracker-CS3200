"""ClinicalTrials.gov API v2: trials by lead sponsor. No key required."""
from pipeline import config
from pipeline.http import ApiClient
from pipeline.normalize import parse_partial_date

_client = ApiClient("https://clinicaltrials.gov/api/v2", config.DEFAULT_USER_AGENT, min_interval=0.25)

_FIELDS = ",".join([
    "NCTId", "LeadSponsorName", "Phase", "OverallStatus", "EnrollmentCount",
    "StartDate", "CompletionDate", "Condition", "InterventionName", "InterventionType",
])


def _parse(study: dict) -> dict:
    ps = study["protocolSection"]
    design = ps.get("designModule", {})
    status = ps.get("statusModule", {})
    phases = [p for p in design.get("phases", []) if p != "NA"]
    interventions = ps.get("armsInterventionsModule", {}).get("interventions", [])
    return {
        "nct_number": ps["identificationModule"]["nctId"],
        "lead_sponsor": ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
        "phase": "/".join(phases) or None,          # e.g. PHASE2/PHASE3
        "status": status.get("overallStatus", "UNKNOWN"),
        "enrollment": design.get("enrollmentInfo", {}).get("count"),
        "start_date": parse_partial_date(status.get("startDateStruct", {}).get("date")),
        "completion_date": parse_partial_date(status.get("completionDateStruct", {}).get("date")),
        "conditions": ps.get("conditionsModule", {}).get("conditions", []),
        "drugs": [i["name"] for i in interventions
                  if i.get("type") in config.DRUG_INTERVENTION_TYPES and i.get("name")],
    }


def trials_by_lead_sponsor(sponsor: str) -> list[dict]:
    """Every study whose lead-sponsor field matches the search term (caller filters exact matches)."""
    params = {"query.lead": sponsor, "fields": _FIELDS, "pageSize": 1000}
    out = []
    while True:
        data = _client.get("studies", params)
        out += [_parse(s) for s in data.get("studies", [])]
        token = data.get("nextPageToken")
        if not token:
            return out
        params["pageToken"] = token
