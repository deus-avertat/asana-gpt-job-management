import datetime
import json
import os
from pprint import pprint

from vendor_setup import ensure_vendor_path

ensure_vendor_path()

import asana
import openai
from asana.rest import ApiException

# Load Config
print("INFO: Loading Config File")
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

openai_client = openai.OpenAI(api_key=config["openai_api_key"])
asana_token = config["asana_token"]
asana_project_id = config["asana_project_id"]
asana_workspace = config["asana_workspace"]

print("INFO: OpenAI API Key Loaded")
print("INFO: Asana API Key Loaded")
print(f"INFO: Set Asana Project ID as: {asana_project_id}")
print(f"INFO: Set Asana Workspace as: {asana_workspace}")
print(f"INFO: Today's Date: {datetime.date.today().isoformat()}")

# DEBUG TASKS
configuration = asana.Configuration()
configuration.access_token = asana_token  # Assigns API key for Asana
api_client = asana.ApiClient(configuration) # Opens an Asana API client

custom_field_settings_api_instance = asana.CustomFieldSettingsApi(api_client)
opts = {
    'limit': 50, # int | Results per page. The number of objects to return per page. The value must be between 1 and 100.
}

try:
    api_response = custom_field_settings_api_instance.get_custom_field_settings_for_project(asana_project_id, opts)
    for data in api_response:
        pprint(data)
except ApiException as e:
    print("Exception when calling CustomFieldSettingsApi->get_custom_field_settings_for_project: %s\n" % e)


