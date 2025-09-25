import copy
import re
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, simpledialog
from typing import Optional

import asana
from asana.rest import ApiException

import functions.ui


@dataclass
class AsanaTaskRequest:
    """Container for the data required to create an Asana task."""

    body: dict
    opts: dict
    bullet_points: list[str]
    task_name: str
    original_email: str


def build_asana_task_request(
    output_text,
    input_text,
    asana_project_id,
    assignee_var,
    priority_var,
    cal_var,
    asana_settings,
) -> Optional[AsanaTaskRequest]:
    """Gather user input and prepare the payload for creating an Asana task."""

    summary_markdown = functions.ui.get_widget_markdown(output_text)
    summary_plain = functions.ui.markdown_to_plain_text(summary_markdown)
    if not summary_plain:
        messagebox.showwarning("Empty", "There is no summary to send.")
        print("WARN: There is no summary to send.")
        return None

    task_name = simpledialog.askstring("Asana Task Name", "Enter the name for the new Asana task:")
    print(f"INFO: Set Task Name: {task_name}")

    if not asana_project_id or not task_name:
        messagebox.showerror("Missing Info", "Task name is required.")
        print("WARN: Task name is required.")
        return None

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

    # Prepare notes and capture the original email before leaving the UI thread
    bullet_point_pattern = r"(?:^\d+\.\s+).+"
    summary_without_tasks = re.sub(bullet_point_pattern, "", summary_plain, flags=re.MULTILINE).strip()
    notes = f"Email: \n{summary_without_tasks}"
    original_email = input_text.get("1.0", tk.END).strip()

    # Priority and additional custom fields
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

    body: dict = {"data": {}}
    task_defaults = {}
    if isinstance(asana_settings, dict):
        defaults_candidate = asana_settings.get("task_defaults", {})
        if isinstance(defaults_candidate, dict):
            task_defaults = copy.deepcopy(defaults_candidate)
    body["data"].update(task_defaults)
    body["data"].setdefault("projects", asana_project_id)
    body["data"]["name"] = task_name
    body["data"]["due_on"] = functions.ui.get_date(cal_var)
    body["data"]["notes"] = notes

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

    opts: dict = {}
    if assignee:
        opts["assignee"] = assignee

    bullet_points = re.findall(r"(?:^[-*]\s+|^\d+\.\s+)(.+)", summary_plain, re.MULTILINE)

    return AsanaTaskRequest(
        body=body,
        opts=opts,
        bullet_points=[point.strip() for point in bullet_points],
        task_name=str(task_name),
        original_email=original_email,
    )


def perform_asana_task_creation(asana_token: str, task_request: AsanaTaskRequest) -> int:
    """Execute the API calls required to create an Asana task.

    Returns the number of subtasks that were created.
    """

    configuration = asana.Configuration()
    configuration.access_token = asana_token
    api_client = asana.ApiClient(configuration)
    tasks_api = asana.TasksApi(api_client)

    task = tasks_api.create_task(task_request.body, task_request.opts)
    task_gid = task.get("gid")
    if not task_gid:
        print("WARN: Asana response did not contain a task GID.")
        raise ValueError("Asana response did not contain a task GID.")

    stories_api = asana.StoriesApi(api_client)
    comment_body = {"data": {"text": task_request.original_email}}
    stories_api.create_story_for_task(comment_body, task_gid, task_request.opts)

    for point in task_request.bullet_points:
        subtask_body = {"data": {"name": point, "parent": task_gid}}
        tasks_api.create_task(subtask_body, {})

    return len(task_request.bullet_points)


def send_to_asana(
    output_text,
    input_text,
    asana_workspace,
    asana_project_id,
    asana_token,
    assignee_var,
    priority_var,
    cal_var,
    asana_settings,
):
    print("INFO: Sending to Asana")
    task_request = build_asana_task_request(
        output_text,
        input_text,
        asana_project_id,
        assignee_var,
        priority_var,
        cal_var,
        asana_settings,
    )
    if not task_request:
        return

    try:
        bullet_count = perform_asana_task_creation(asana_token, task_request)
        messagebox.showinfo(
            "Success",
            f"Task '{task_request.task_name}' created in Asana with {bullet_count} sub-tasks.",
        )
        print(
            f"INFO: Task '{task_request.task_name}' created in Asana with {bullet_count} sub-tasks."
        )
    except ApiException as exc:
        messagebox.showerror("Asana API Error", str(exc))
        print(f"ERR: Asana API Error: {exc}")
    except Exception as exc:  # pragma: no cover - defensive programming
        messagebox.showerror("Asana Error", str(exc))
        print(f"ERR: Asana Error: {exc}")