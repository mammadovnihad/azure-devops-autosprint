import datetime
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
        name: str = team.get("name")

        team_ids.append({"id": id, "name": name})

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

            teams_list = handle_paginated_results(
                f"/_apis/projects/{project_id}/teams", get_teams_by_projects_handler)

            teams = []
            for team in teams_list:
                last_iteration_list = handle_paginated_results(
                    f"/{project_id}/{team['id']}/_apis/work/teamsettings/iterations", get_last_iteration_by_teams_handler)

                last_iteration = None
                if last_iteration_list:
                    last_iteration = last_iteration_list[0]
                else:
                    last_iteration = None

                teams.append({"id": team["id"],
                              "name": team["name"],
                              "last_iteration": {
                                  "id": last_iteration["id"],
                                  "name": last_iteration["name"],
                                  "startDate": last_iteration["attributes"]["startDate"],
                                  "finishDate": last_iteration["attributes"]["finishDate"]
                } if last_iteration is not None else None})

            active_projs.append(
                {"id": project_id, "name": name, "sprint_length": sprint_length, "teams": teams})

    return active_projs


def find_next_workday():
    current_date = datetime.datetime.now()
    while True:
        # Increment the current date by one day
        current_date += datetime.timedelta(days=1)

        # Check if the day of the week is not a weekend (Monday to Friday)
        if current_date.weekday() < 5:
            return current_date


def create_new_sprint(project_id, team_id, team_name, last_iteration_finish_date, last_iteration_num, sprint_length):
    new_sprint_name = f"Iteration {last_iteration_num + 1}"
    new_sprint_startDate = find_next_workday()
    new_sprint_finishDate = new_sprint_startDate + \
        datetime.timedelta(days=(sprint_length - 1))

    cn_req = {
        "name": f"{team_name} {new_sprint_name}",
        "attributes": {
            "startDate": new_sprint_startDate.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "finishDate": new_sprint_finishDate.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
    }

    headers = {'Content-Type': 'application/json'}

    cn_url = f"{BASE_URL}/{project_id}/_apis/wit/classificationnodes/iterations?api-version=7.1-preview.2"
    r_cn = s.post(cn_url,
                  timeout=int(os.environ["HTTP_TIMEOUT"]), headers=headers, data=json.dumps(cn_req))

    # TODO Separate iteration request
    cn_data = r_cn.json()

    new_iteration_id = cn_data["identifier"]

    iter_req = {
        "id": new_iteration_id,
    }

    iter_url = f"{BASE_URL}/{project_id}/{team_id}/_apis/work/teamsettings/iterations?api-version=7.2-preview.1"
    r_iter = s.post(iter_url,
                    timeout=int(os.environ["HTTP_TIMEOUT"]), headers=headers, data=json.dumps(iter_req))

    print(
        f"Sprint created: {cn_req['name']} | {cn_req['attributes']['startDate']}-{cn_req['attributes']['finishDate']}")

    return


if __name__ == "__main__":
    start_time = time.time()

    active_projs = handle_paginated_results(
        "/_apis/projects", get_active_projs_handler)

    filtered_projects = []

    for project in active_projs:
        project_id = project["id"]
        project_sprint_length = project["sprint_length"]

        for team in project["teams"]:
            team_id = team["id"]
            team_name = team["name"]

            if (team["last_iteration"] is not None):
                last_iteration_finish_date = datetime.datetime.strptime(
                    team["last_iteration"]["finishDate"], "%Y-%m-%dT%H:%M:%SZ")
                time_difference = last_iteration_finish_date - datetime.datetime.now()

                if time_difference <= datetime.timedelta(days=1):
                    filtered_projects.append(project)

                    last_iteration_name: str = team["last_iteration"]["name"]
                    last_iteration_num = int(
                        last_iteration_name.split(" ")[-1])

                    create_new_sprint(
                        project_id, team_id, team_name, last_iteration_finish_date, last_iteration_num, project_sprint_length)
            else:
                filtered_projects.append(project)

                last_iteration_finish_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                last_iteration_num = 0

                create_new_sprint(
                    project_id, team_id, team_name, last_iteration_finish_date, last_iteration_num, project_sprint_length)

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"\nExecution time: {execution_time:.5f} seconds")
