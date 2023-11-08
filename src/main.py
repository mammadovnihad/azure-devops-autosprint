import json
import re
import time
from requests.auth import HTTPBasicAuth
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = F"https://dev.azure.com/{os.environ['ORGANIZATION']}"

s = requests.Session()
s.auth = HTTPBasicAuth("", os.environ["PAT"])

def handle_paginated_results(url_segment, handler_func):
    count = 1
    top = 10
    skip = 0
    req_no = 1
    results = []

    while count == top or req_no == 1:
        url = f"{BASE_URL}{url_segment}{'?' if '?' not in url_segment else '&'}$top={top}&$skip={skip}&api-version=7.2-preview.3"

        r = s.get(url,
                  timeout=int(os.environ["HTTP_TIMEOUT"]))
        body = r.json()

        data = body["value"]

        results.extend(handler_func(data))

        count = body["count"]
        skip = skip + top
        req_no = req_no + 1

    return results

def get_teams_by_projects_handler(teams):
    team_ids = []

    for team in teams:
        id: str = team.get("id")

        team_ids.append(id)

    return team_ids

def extract_number_from_tag(tag):
    # Use a regular expression to find and extract the number part
    match = re.search(r'#days(\d+)', tag)

    if match:
        # Return the extracted number as an integer
        return int(match.group(1))
    else:
        # Return default (7) if no match is found
        return 7

def get_active_projs_handler(projects):
    active_projs = []

    for proj in projects:
        description: str = proj.get("description")

        if description is not None and "#active" in description:
            project_id: str = proj.get("id")
            name: str = proj.get("name")
            sprint_length = extract_number_from_tag(description)

            team_ids = handle_paginated_results(
                f"/_apis/projects/{project_id}/teams", get_teams_by_projects_handler)

            active_projs.append(
                {"id": project_id, "name": name, "sprint_length": sprint_length, "team_ids": team_ids})

    return active_projs

if __name__ == "__main__":
    start_time = time.time()

    active_projs = handle_paginated_results(
        "/_apis/projects", get_active_projs_handler)

    print(json.dumps(active_projs, indent=4))

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Execution time: {execution_time:.5f} seconds")
