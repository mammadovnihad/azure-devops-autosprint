import json
import re
from requests.auth import HTTPBasicAuth
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = F"https://dev.azure.com/{os.environ['ORGANIZATION']}"

s = requests.Session()
s.auth = HTTPBasicAuth("", os.environ["PAT"])

def extract_number_from_tag(tag):
    # Use a regular expression to find and extract the number part
    match = re.search(r'#days(\d+)', tag)

    if match:
        # Return the extracted number as an integer
        return int(match.group(1))
    else:
        # Return default (7) if no match is found
        return 7

def get_active_projs():
    count = 1
    top = 10
    skip = 0
    req_no = 1
    active_projs = []

    while count == top or req_no == 1:
        r = s.get(f"{BASE_URL}/_apis/projects?$top={top}&$skip={skip}&api-version=7.2-preview.4",
                  timeout=int(os.environ["HTTP_TIMEOUT"]))
        body = r.json()

        projects = body["value"]

        for proj in projects:
            description: str = proj.get("description")

            if description is not None and "#active" in description:
                id: str = proj.get("id")
                name: str = proj.get("name")
                sprint_length = extract_number_from_tag(description)

                active_projs.append(
                    {"id": id, "name": name, "sprint_length": sprint_length})

        count = body["count"]
        skip = skip + top
        req_no = req_no + 1

    return active_projs


if __name__ == "__main__":
    active_projs = get_active_projs()

    for proj in active_projs:
        print(f"{proj['id']} {proj['name']} {proj['sprint_length']}")
