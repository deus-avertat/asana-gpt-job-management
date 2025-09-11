import tkinter as tk
import asana
from asana.rest import ApiException
import re
from tkinter import messagebox, simpledialog

import functions.ui

def send_to_asana(output_text, input_text,
                  asana_workspace, asana_project_id, asana_token,
                  assignee_var, priority_var, cal_var):
    print("INFO: Sending to Asana")
    summary = output_text.get("1.0", tk.END).strip()
    if not summary:
        messagebox.showwarning("Empty", "There is no summary to send.")
        print(f"WARN: There is no summary to send.")
        return

    task_name = simpledialog.askstring("Asana Task Name", "Enter the name for the new Asana task:")
    print(f"INFO: Set Task Name: {task_name}")
    assignee_raw = assignee_var.get()
    assignee = assignee_raw.lower()
    if assignee == "tristan":
        assignee = f"tristan@{asana_workspace}"
        print(f"INFO: Set Assignee: {assignee}")
    elif assignee == "kynan":
        assignee = f"kynan@{asana_workspace}"
        print(f"INFO: Set Assignee: {assignee}")
    else:
        assignee = ""
        print(f"INFO: Assignee: None Specified")

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

        # Get Priority
        priority_mapping = {
            "None": "1201356624548797",
            "Low": "1201356624548796",
            "Medium": "1201356624548795",
            "High": "1201356624548794",
            "Today": "1201356624548793",
            "Urgent": "1201356624548792"
        }
        priority_selection = priority_var.get()
        priority_field_id = "1201356624548791"
        custom_fields = {
            priority_field_id: priority_mapping.get(priority_selection)
        }

        body = {"data": {
            "name": task_name, # Job Name
            "projects": asana_project_id, # Job Project (Business Tasks)
            "due_on": functions.ui.get_date(cal_var),
            "notes": notes # Job Description
        }}
        body["data"]["custom_fields"] = custom_fields
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