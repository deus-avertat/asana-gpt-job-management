import copy
import tkinter as tk
import asana
from asana.rest import ApiException
import re
from tkinter import messagebox, simpledialog

import functions.ui

def send_to_asana(output_text, input_text,
                  asana_workspace, asana_project_id, asana_token,
                  assignee_var, priority_var, cal_var, asana_settings):
    print("INFO: Sending to Asana")
    summary = output_text.get("1.0", tk.END).strip()
    if not summary:
        messagebox.showwarning("Empty", "There is no summary to send.")
        print(f"WARN: There is no summary to send.")
        return

    task_name = simpledialog.askstring("Asana Task Name", "Enter the name for the new Asana task:")
    print(f"INFO: Set Task Name: {task_name}")
    assignee = ""
    assignee_lookup = {}
    if isinstance(asana_settings, dict):
        lookup = asana_settings.get("assignees", {})
        if isinstance(lookup, dict):
            assignee_lookup = lookup
    assignee_raw = assignee_var.get()
    if isinstance(assignee_raw, str):
        assignee = assignee_lookup.get(assignee_raw.casefold(), "")
    if assignee:
        print(f"INFO: Set Assignee: {assignee}")
    else:
        assignee = ""
        print("INFO: Assignee: None Specified")

    if not asana_project_id or not task_name:
        messagebox.showerror("Missing Info", "Task name is required.")
        print(f"WARN: Task name is required.")
        return

    try:
        configuration = asana.Configuration()
        configuration.access_token = asana_token # Assigns API key for Asana
        api_client = asana.ApiClient(configuration) # Opens an Asana API client
        tasks_api = asana.TasksApi(api_client) # Opens an Asana Task API client
        # email_text = input_text.get("1.0", tk.END).strip()
        bullet_point_pattern = r"(?:^[-*]\s+|^\d+\.\s+).+" # Finds bullet points in summary
        summary_without_tasks = re.sub(bullet_point_pattern, "", summary, flags=re.MULTILINE).strip() # Strips bullet point tasks from summary
        notes = f"Email: \n{summary_without_tasks}" # Formats description of Asana job

        # Get Priority - This section is dependent on your Asana setup. We use tags to assign priority. This field can be edited to suit and tags you wish to assign.
        priority_mapping = {}
        priority_field_id = None
        custom_fields = {}
        if isinstance(asana_settings, dict):
            priority_mapping_candidate = asana_settings.get("priority_options", {})
            if isinstance(priority_mapping_candidate, dict):
                priority_mapping = priority_mapping_candidate
            priority_field_id_candidate = asana_settings.get("priority_field_id")
            if isinstance(priority_field_id_candidate, str) and priority_field_id_candidate:
                priority_field_id = priority_field_id_candidate
        priority_selection = priority_var.get()
        if priority_field_id and isinstance(priority_selection, str) and priority_selection in priority_mapping:
            custom_fields[priority_field_id] = priority_mapping[priority_selection]

        body = {"data": {}}
        task_defaults = {}
        if isinstance(asana_settings, dict):
            defaults_candidate = asana_settings.get("task_defaults", {})
            if isinstance(defaults_candidate, dict):
                task_defaults = copy.deepcopy(defaults_candidate)
        body["data"].update(task_defaults)
        body["data"].setdefault("projects", asana_project_id) # Job Project (Business Tasks)
        body["data"]["name"] = task_name # Job Name
        body["data"]["due_on"] = functions.ui.get_date(cal_var)
        body["data"]["notes"] = notes # Job Description

        existing_custom_fields = body["data"].get("custom_fields", {})
        merged_custom_fields = {}
        if isinstance(existing_custom_fields, dict):
            merged_custom_fields.update(existing_custom_fields)
        if isinstance(custom_fields, dict):
            merged_custom_fields.update(custom_fields)
        additional_custom_fields = {}
        if isinstance(asana_settings, dict):
            additional_candidate = asana_settings.get("custom_fields", {})
            if isinstance(additional_candidate, dict):
                additional_custom_fields = additional_candidate
        if additional_custom_fields:
            merged_custom_fields.update(additional_custom_fields)
        if merged_custom_fields:
            body["data"]["custom_fields"] = merged_custom_fields
        opts = {}

        if assignee:
            opts["assignee"] = assignee # Person who gets the job

        task = tasks_api.create_task(body, opts) # Creates the Asana job
        task_gid = task["gid"] if "gid" in task else None # Gets GID from the created job
        if not task_gid:
            print("WARN: Asana response did not contain a task GID.")
            raise ValueError("Asana response did not contain a task GID.")

        # Add original email as a comment
        stories_api = asana.StoriesApi(api_client)
        original_email = input_text.get("1.0", tk.END).strip()
        comment_body = {
            "data": {
                "text": f"{original_email}"
            }
        }
        stories_api.create_story_for_task(comment_body, task_gid, opts)

        # Convert tasks provided by ChatGPT into subtasks for the job
        bullet_points = re.findall(r"(?:^[-*]\s+|^\d+\.\s+)(.+)", summary, re.MULTILINE)
        for point in bullet_points:
            subtask_body = {"data": {"name": point.strip(), "parent": task_gid}}
            tasks_api.create_task(subtask_body, {})

        messagebox.showinfo("Success", f"Task '{task_name}' created in Asana with {len(bullet_points)} sub-tasks.")
        print(f"INFO: Task '{task_name}' created in Asana with {len(bullet_points)} sub-tasks.")
    except ApiException as e:
        messagebox.showerror("Asana API Error", str(e))
        print(f"ERR: Asana API Error: {e}")
    except Exception as e:
        messagebox.showerror("Asana Error", str(e))
        print(f"ERR: Asana Error: {e}")