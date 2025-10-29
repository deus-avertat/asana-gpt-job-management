import copy
import re
import sys
import tkinter as tk
import traceback
from contextlib import suppress
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

class _TaskNameDialog:
    """Simple modal dialog to request the Asana task name.

    ``tkinter.simpledialog`` occasionally fails to open in frozen builds when
    Tcl cannot resolve its themed dialog resources.  Falling back to a
    lightweight custom dialog keeps the workflow usable while still behaving
    modally with the parent window.
    """

    def __init__(self, parent: tk.Misc | None) -> None:
        self._parent = parent
        self.result: Optional[str] = None
        self._top = tk.Toplevel(parent)
        self._top.title("Asana Task Name")
        with suppress(tk.TclError):
            self._top.transient(parent)
        with suppress(tk.TclError):
            self._top.grab_set()
        with suppress(tk.TclError):
            self._top.lift()
        self._top.resizable(False, False)
        self._top.protocol("WM_DELETE_WINDOW", self._cancel)

        frame = tk.Frame(self._top, padx=12, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(
            frame,
            text="Enter the name for the new Asana task:",
            justify="left",
        )
        label.pack(anchor="w")

        with suppress(tk.TclError):
            self._top.update_idletasks()

        self._entry = tk.Entry(frame, width=40)
        self._entry.pack(fill=tk.X, pady=(8, 10))
        with suppress(tk.TclError):
            self._entry.focus_set()

        button_row = tk.Frame(frame)
        button_row.pack(fill=tk.X)

        ok_button = tk.Button(button_row, text="OK", command=self._accept)
        ok_button.pack(side="right", padx=(4, 0))
        cancel_button = tk.Button(button_row, text="Cancel", command=self._cancel)
        cancel_button.pack(side="right")

        self._top.bind("<Return>", lambda *_: self._accept())
        self._top.bind("<Escape>", lambda *_: self._cancel())

    def _accept(self) -> None:
        value = self._entry.get().strip()
        self.result = value if value else None
        self._top.destroy()

    def _cancel(self) -> None:
        self.result = None
        self._top.destroy()

    def show(self) -> Optional[str]:
        parent = self._parent
        if parent is not None:
            try:
                parent.wait_window(self._top)
            except tk.TclError:  # pragma: no cover - defensive fallback
                self._top.wait_window()
        else:  # pragma: no cover - defensive fallback
            self._top.wait_window()
        return self.result


def _prompt_task_name(parent_widget: tk.Misc | None) -> Optional[str]:
    """Collect the Asana task name from the user.

    Frozen builds occasionally struggle to show the themed ``simpledialog``
    prompt.  Prefer the lightweight custom dialog when the app is frozen and
    fall back to it whenever Tk raises an unexpected exception.  This keeps the
    button responsive instead of bubbling the error up to the caller.
    """

    def _show_custom_dialog() -> Optional[str]:
        try:
            dialog = _TaskNameDialog(parent_widget)
        except Exception as dialog_exc:  # pragma: no cover - defensive fallback
            print(f"ERR: Failed to open fallback task dialog: {dialog_exc}")
            traceback.print_exc()
            return None
        return dialog.show()

    # When running from PyInstaller (``sys.frozen``) skip the native dialog.
    if getattr(sys, "frozen", False):  # pragma: no cover - depends on build env
        return _show_custom_dialog()

    try:
        return simpledialog.askstring(
            "Asana Task Name",
            "Enter the name for the new Asana task:",
            parent=parent_widget,
        )
    except Exception as exc:  # pragma: no cover - only surfaces in frozen app
        print(f"ERR: Failed to open simpledialog for task name: {exc}")
        traceback.print_exc()
        return _show_custom_dialog()

def build_asana_task_request(
    output_text,
    input_text,
    asana_project_id,
    assignee_var,
    priority_var,
    cal_var,
    asana_settings,
    *,
    parent=None,
) -> Optional[AsanaTaskRequest]:
    """Gather user input and prepare the payload for creating an Asana task."""

    parent_widget = parent
    if parent_widget is None:
        try:
            parent_widget = output_text.winfo_toplevel()
        except Exception: # pragma: no cover - best effort fallback
            parent_widget = None

    try:
        summary_markdown = functions.ui.get_widget_markdown(output_text)
    except Exception as exc:  # pragma: no cover - unexpected widget shape
        print(f"ERR: Failed to read summary markdown: {exc}")
        traceback.print_exc()
        summary_markdown = ""

    try:
        summary_plain = functions.ui.markdown_to_plain_text(summary_markdown)
    except Exception as exc:  # pragma: no cover - dependency mismatch fallback
        print(f"ERR: Failed to convert markdown to plain text: {exc}")
        traceback.print_exc()
        summary_plain = summary_markdown.strip()
    if not summary_plain:
        messagebox.showwarning(
            "Empty", "There is no summary to send.", parent=parent_widget
        )
        print("WARN: There is no summary to send.")
        return None

    task_name = _prompt_task_name(parent_widget)
    print(f"INFO: Set Task Name: {task_name}")

    if not asana_project_id or not task_name:
        messagebox.showerror(
            "Missing Info", "Task name is required.", parent=parent_widget
        )
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
    try:
        original_email = input_text.get("1.0", tk.END).strip()
    except Exception as exc:  # pragma: no cover - unexpected widget shape
        print(f"ERR: Failed to read original email: {exc}")
        traceback.print_exc()
        original_email = ""

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
    # body["data"].setdefault("projects", asana_project_id)

    projects_value = body["data"].get("projects")
    normalized_projects: list[str] = []

    def add_project_id(value) -> None:
        """Collect a project gid from the various shapes Asana accepts."""

        if isinstance(value, str):
            project_id = value.strip()
            if project_id and project_id not in normalized_projects:
                normalized_projects.append(project_id)
        elif isinstance(value, dict):
            gid = value.get("gid")
            if isinstance(gid, str):
                add_project_id(gid)

    if isinstance(projects_value, (list, tuple, set)):
        for candidate in projects_value:
            add_project_id(candidate)
    else:
        add_project_id(projects_value)

    if isinstance(asana_project_id, (list, tuple, set)):
        for candidate in asana_project_id:
            add_project_id(candidate)
    else:
        add_project_id(asana_project_id)

    if normalized_projects:
        body["data"]["projects"] = normalized_projects
    elif "projects" in body["data"]:
        body["data"].pop("projects")

    body["data"]["name"] = task_name
    try:
        due_on = functions.ui.get_date(cal_var)
    except Exception as exc:  # pragma: no cover - unexpected widget state
        print(f"ERR: Failed to read calendar selection: {exc}")
        traceback.print_exc()
        due_on = ""

    body["data"]["due_on"] = due_on
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
        body["data"]["assignee"] = assignee

    bullet_points = re.findall(r"^\d+\.\s+(.+)", summary_plain, re.MULTILINE)

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
    *,
    parent=None,
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
        parent=parent,
    )
    if not task_request:
        return

    try:
        bullet_count = perform_asana_task_creation(asana_token, task_request)
        messagebox.showinfo(
            "Success",
            f"Task '{task_request.task_name}' created in Asana with {bullet_count} sub-tasks.",
            parent=parent,
        )
        print(
            f"INFO: Task '{task_request.task_name}' created in Asana with {bullet_count} sub-tasks."
        )
    except ApiException as exc:
        messagebox.showerror("Asana API Error", str(exc), parent=parent)
        print(f"ERR: Asana API Error: {exc}")
    except Exception as exc:  # pragma: no cover - defensive programming
        messagebox.showerror("Asana Error", str(exc), parent=parent)
        print(f"ERR: Asana Error: {exc}")