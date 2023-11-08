# AutoSprint -  Sprint Management tool for Azure DevOps

This script interacts with the [Azure DevOps Services API](https://learn.microsoft.com/en-us/rest/api/azure/devops/?view=azure-devops-rest-7.2) to manage sprints and iterations for active projects and teams. It does the following:

1. Retrieves active projects with specific tags (Checks the project descriptions for `#active` keyword).
2. Checks if the last iteration for each team in a project has finished within the last day.
3. Creates a new sprint/iteration for teams that meet the condition (Uses `#days*` [for ex. `#days7`, `#days14`] tag/keyword for the Sprint length, default is 7 if not found).

## Prerequisites

- Python 3.x
- Install required dependencies using: `pip install -r requirements.txt`

## Configuration

1. Create a `.env` file in the root directory with the following variables:
   ```
   ORGANIZATION=your_organization_name
   PAT=your_personal_access_token
   HTTP_TIMEOUT=timeout_in_seconds
   ```

## Usage

Run the script using the following command:

```bash
python src/main.py
```

## Additional Notes

- The script uses the `requests` library to interact with the Azure DevOps REST API.
- It checks for active projects and their teams, filters based on the last iteration's finish date, and creates a new sprint if necessary.
- The script measures execution time and prints it at the end.

Feel free to modify the script or the README as needed for your specific use case.

Make sure to replace `your_organization_name` and `your_personal_access_token` with your actual Azure DevOps organization name and personal access token in the `.env` file.

Additionally, you might want to update the `requirements.txt` file with the actual dependencies required by your script. If you haven't already, you can create it manually or use `pip freeze > requirements.txt` after installing the necessary packages.