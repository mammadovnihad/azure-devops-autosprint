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
        url = f"{BASE_URL}{url_segment}{'?' if '?' not in url_segment else '&'}$top={top}&$skip={skip}&api-version=7.2-preview.1"

        r = s.get(url,
                  timeout=int(os.environ["HTTP_TIMEOUT"]))
        body = r.json()

        data = body["value"]

        result = handler_func(data)
        if result is not None:
            results.extend(result)

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


def get_last_iteration_by_teams_handler(iterations):
    if iterations:
        last_iteration = [iterations[-1]]
    else:
        last_iteration = None

    return last_iteration


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

            teams = []
            for team_id in team_ids:
                last_iteration_list = handle_paginated_results(
                    f"/{project_id}/{team_id}/_apis/work/teamsettings/iterations", get_last_iteration_by_teams_handler)

                last_iteration = None
                if last_iteration_list:
                    last_iteration = last_iteration_list[0]
                else:
                    last_iteration = None

                teams.append({"id": team_id,
                              "last_iteration": {
                                  "id": last_iteration["id"],
                                  "name": last_iteration["name"],
                                  "startDate": last_iteration["attributes"]["startDate"],
                                  "finishDate": last_iteration["attributes"]["finishDate"]
                              } if last_iteration is not None else None})

            active_projs.append(
                {"id": project_id, "name": name, "sprint_length": sprint_length, "teams": teams})

    return active_projs

if __name__ == "__main__":
    start_time = time.time()

    active_projs = handle_paginated_results(
        "/_apis/projects", get_active_projs_handler)

    print(json.dumps(active_projs, indent=4))

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Execution time: {execution_time:.5f} seconds")
