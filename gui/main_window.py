import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from vendor_setup import ensure_vendor_path

ensure_vendor_path()

import markdown
from openai import OpenAIError
from tkcalendar import DateEntry
from tkhtmlview import HTMLScrolledText

import functions.asana_api
import functions.database
import functions.gpt
import functions.ui
from functions.files import extract_text_from_file
from gui.invoice_window import create_invoice_window

# GUI ----------------------------------------------------------------

def create_main_window(openai_service, config: dict) -> None:
    """Build and run the main Tkinter UI."""
    asana_token = config["asana_token"]
    asana_project_id = config["asana_project_id"]
    asana_workspace = config["asana_workspace"]

    # Build configurable Asana metadata -------------------------------------
    assignee_options_raw = config.get("asana_assignees", [])
    assignee_choices = []
    assignee_lookup = {}
    if isinstance(assignee_options_raw, list):
        for entry in assignee_options_raw:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                continue
            raw_value = (
                entry.get("gid")
                or entry.get("email")
                or entry.get("value")
                or ""
            )
            if isinstance(raw_value, str):
                value = raw_value.replace("{workspace}", asana_workspace)
            else:
                value = ""
            assignee_choices.append(name)
            assignee_lookup[name.casefold()] = value
    if not assignee_choices:
        assignee_choices = ["Unassigned"]
    if not any(choice.casefold() == "unassigned" for choice in assignee_choices):
        assignee_choices.append("Unassigned")
    assignee_lookup.setdefault("unassigned", "")
    assignee_choices = list(dict.fromkeys(assignee_choices))
    default_assignee = config.get("asana_default_assignee")
    if not isinstance(default_assignee, str) or default_assignee not in assignee_choices:
        default_assignee = assignee_choices[0]

    priority_options_raw = config.get("asana_priority_options")
    priority_mapping = {}
    if isinstance(priority_options_raw, dict):
        for label, value in priority_options_raw.items():
            if isinstance(label, str):
                priority_mapping[label] = value
    priority_field_id = config.get("asana_priority_field_id")
    if not isinstance(priority_field_id, str) or not priority_field_id.strip():
        priority_field_id = None
    default_priority = config.get("asana_default_priority")
    if priority_mapping:
        if not isinstance(default_priority, str) or default_priority not in priority_mapping:
            default_priority = next(iter(priority_mapping))
        priority_choices = list(priority_mapping.keys())
    else:
        if not isinstance(default_priority, str) or not default_priority:
            default_priority = "None"
        priority_choices = [default_priority]

    additional_custom_fields = config.get("asana_custom_fields")
    if not isinstance(additional_custom_fields, dict):
        additional_custom_fields = {}

    task_defaults = config.get("asana_task_defaults")
    if not isinstance(task_defaults, dict):
        task_defaults = {}

    asana_settings = {
        "assignees": assignee_lookup,
        "priority_field_id": priority_field_id,
        "priority_options": priority_mapping,
        "custom_fields": additional_custom_fields,
        "task_defaults": task_defaults,
    }

    print("INFO: Initialising History Database")
    functions.database.init_history_db()

    print("INFO: OpenAI API Key Loaded")
    print("INFO: Asana API Key Loaded")
    print(f"INFO: Set Asana Project ID as: {asana_project_id}")
    print(f"INFO: Set Asana Workspace as: {asana_workspace}")
    print(f"INFO: Today's Date: {datetime.date.today().isoformat()}")

    # Root Window
    root = tk.Tk()
    root.title("ChatGPT Email Assistant")
    root.geometry("800x960")

    default_model = config.get("default_model", "gpt-4")

    # Shared model selection across windows
    model_list_var = tk.StringVar(value=default_model)
    root.shared_model_var = model_list_var

    invoice_window = None

    def show_main() -> None:
        print("INFO: Switching to Main Window")
        if invoice_window is not None:
            invoice_window.withdraw()
        root.deiconify()
        root.lift()

    invoice_window = create_invoice_window(root, openai_service, config, show_main)
    invoice_window.withdraw()

    # Email Input
    input_label = tk.Label(root, text="Paste Email Content Here:")
    input_label.pack()

    input_text = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD)
    input_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)

    output_label = tk.Label(root, text="ChatGPT Output:")
    output_text = HTMLScrolledText(root, height=10)

    # Email history
    history_frame = tk.Frame(root)
    history_frame.pack(pady=5)

    history_list = tk.Menubutton(history_frame, text="Load History", relief="groove")
    history_list.menu = tk.Menu(history_list, tearoff=0)
    history_list["menu"] = history_list.menu
    history_list.pack(side="left")

    refresh_button = tk.Button(
        history_frame,
        text="↻",
        command=lambda: functions.database.load_history(history_list, input_text, output_text),
    )
    refresh_button.pack(side="left", padx=5)

    # Button Frames
    button_frame_main = tk.Frame(root)
    button_frame_main.pack()

    button_frame_left = tk.Frame(button_frame_main)
    button_frame_left.grid(column=0, row=0, padx=10)
    button_frame_left_top = tk.Frame(button_frame_left, bd=1, relief="groove", pady=5)
    button_frame_left_top.pack(pady=5)
    button_frame_left_bottom = tk.Frame(button_frame_left, bd=1, relief="groove", pady=5)
    button_frame_left_bottom.pack(pady=10)

    button_frame_right = tk.Frame(button_frame_main)
    button_frame_right.grid(column=1, row=0, padx=10)
    button_frame_right_top = tk.Frame(button_frame_right, bd=1, relief="groove", pady=5)
    button_frame_right_top.pack(pady=5)
    button_frame_right_bottom = tk.Frame(button_frame_right, bd=1, relief="groove", pady=5)
    button_frame_right_bottom.pack(pady=10)

    model_list_label = tk.Label(button_frame_right_top, text="Select GPT Model")
    model_list_label.config(font=("Segoe UI", 9, "bold"))
    model_list_label.grid(row=0, column=0, padx=5)

    model_list = ttk.OptionMenu(
        button_frame_right_top,
        model_list_var,
        default_model,
        "gpt-4",
        "gpt-4.1",
        "gpt-5",
        "o4-mini",
    )
    model_list.grid(row=1, column=0, padx=5)

    # Variables for ChatGPT output
    tone_var = tk.StringVar(value="Professional")
    length_var = tk.StringVar(value="Short")
    draft_length_map = {
        "Short": "one to two sentence",
        "Medium": "one paragraph",
        "Long": "two paragraph",
    }

    # OpenAI function
    def call_openai(prompt: str, output_widget: HTMLScrolledText, mode: str) -> None:
        try:
            reply = openai_service.generate_response(model_list_var.get(), prompt)
            print("INFO: Saving to local history")
            functions.database.save_to_history(mode, tone_var.get(), prompt, reply)
            output_widget.config(state=tk.NORMAL)
            output_widget.raw_markdown = reply
            output_widget.set_html(markdown.markdown(reply))
        except OpenAIError as e:
            messagebox.showerror("OpenAI Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    attached_file_path = None

    # Attach file function (WIP)
    def attach_file() -> None:
        nonlocal attached_file_path
        file_path = filedialog.askopenfilename(
            title="Select a file to attach",
            filetypes=[
                ("Text files", "*.txt"),
                ("PDF files", "*.pdf"),
                ("Word files", "*.docx"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            attached_file_path = file_path
            print(f"INFO: Attached file: {file_path}")

    def show_invoice_window() -> None:
        print("INFO: Switching to Invoice Window")
        root.withdraw()
        invoice_window.deiconify()
        invoice_window.lift()

    # Summarize content in the email field
    summarize_button = tk.Button(
        button_frame_left_top,
        text="Summarise",
        command=lambda: functions.gpt.summarize(
            input_text.get("1.0", tk.END).strip(),
            model_list_var.get(),
            output_text,
            attached_file_checkbox_var,
            attached_file_path,
            extract_text_from_file,
            task_checkbox_var,
            fixes_checkbox_var,
            lambda p, o: call_openai(p, o, "summarize"),
        ),
    )
    summarize_button.grid(row=0, column=0, padx=5)

    # Draft response based on content in the email field
    draft_button = tk.Button(
        button_frame_left_top,
        text="Draft Reply",
        command=lambda: functions.gpt.draft_reply(
            tone_var,
            draft_length_map[length_var.get()],
            input_text,
            output_text,
            lambda p, o: call_openai(p, o, "draft"),
        ),
    )
    draft_button.grid(row=0, column=1, padx=5)

    # Attach file button
    attach_button = tk.Button(button_frame_left_top, text="Attach Document", command=attach_file)
    attach_button.grid(row=0, column=2, padx=5)

    # Copy response text
    copy_button = tk.Button(
        button_frame_left_bottom,
        text="Copy Output",
        command=lambda: functions.ui.copy_output(root, output_text),
    )
    copy_button.grid(row=1, column=0, padx=5)

    # Send job to asana button
    asana_button = tk.Button(
        button_frame_left_bottom,
        text="Add to Asana",
        command=lambda: functions.asana_api.send_to_asana(
            output_text,
            input_text,
            asana_workspace,
            asana_project_id,
            asana_token,
            assignee_var,
            priority_var,
            cal_var,
            asana_settings,
        ),
    )
    asana_button.grid(row=1, column=1, padx=5)

    invoice_button = tk.Button(
        button_frame_right_bottom,
        text="Switch to Invoicing Notes",
        command=show_invoice_window,
    )
    invoice_button.grid(row=0, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="ew")

    options_frame = tk.Frame(root)
    options_frame.pack()

    draft_frame = tk.Frame(options_frame, bd=1, relief="groove")
    draft_frame.grid(row=0, column=1)

    tone_label = tk.Label(draft_frame, text="Select Tone for Drafted Reply:")
    tone_label.config(font=("Segoe UI", 9, "bold"))
    tone_label.grid(row=0, column=1, padx=5)

    tone_menu = ttk.OptionMenu(draft_frame, tone_var, "Professional", "Professional", "Semi-professional", "Casual")
    tone_menu.grid(row=1, column=1, padx=5)

    length_label = tk.Label(draft_frame, text="Select Length for Drafted Reply:")
    length_label.config(font=("Segoe UI", 9, "bold"))
    length_label.grid(row=2, column=1, padx=5)

    length_menu = ttk.OptionMenu(draft_frame, length_var, "Short", "Short", "Medium", "Long")
    length_menu.grid(row=3, column=1, padx=5)

    checkbox_frame = tk.Frame(options_frame, bd=1, relief="groove")
    checkbox_frame.grid(row=0, column=2, padx=5)

    task_checkbox_var = tk.BooleanVar()
    task_checkbox = tk.Checkbutton(
        checkbox_frame,
        text="Include task list in summary?",
        variable=task_checkbox_var,
    )
    task_checkbox.grid(row=1, column=0, padx=5)

    fixes_checkbox_var = tk.BooleanVar()
    fixes_checkbox = tk.Checkbutton(
        checkbox_frame,
        text="Provide possible solutions to issue?",
        variable=fixes_checkbox_var,
    )
    fixes_checkbox.grid(row=2, column=0, padx=5)

    attached_file_checkbox_var = tk.BooleanVar()
    attached_file_checkbox = tk.Checkbutton(
        checkbox_frame,
        text="Summarise attached document?",
        variable=attached_file_checkbox_var,
    )
    attached_file_checkbox.grid(row=3, column=0, padx=5)

    assignee_frame = tk.Frame(options_frame, bd=1, relief="groove")
    assignee_frame.grid(row=0, column=3, padx=5)

    assignee_label = tk.Label(assignee_frame, text="Assignee")
    assignee_label.config(font=("Segoe UI", 9, "bold"))
    assignee_label.grid(row=0, column=0, padx=5)

    assignee_var = tk.StringVar(value=default_assignee)
    assignee_menu_choices = [default_assignee] + [choice for choice in assignee_choices if choice != default_assignee]
    assignee_menu = ttk.OptionMenu(
        assignee_frame,
        assignee_var,
        default_assignee,
        *assignee_menu_choices,
    )
    assignee_menu.grid(row=1, column=0, padx=5)

    cal_label = tk.Label(assignee_frame, text="Due Date")
    cal_label.config(font=("Segoe UI", 9, "bold"))
    cal_label.grid(row=0, column=1, padx=5)

    cal_var = DateEntry(assignee_frame, date_pattern="yyyy-mm-dd")
    cal_var.grid(row=1, column=1, padx=5)

    priority_label = tk.Label(assignee_frame, text="Priority")
    priority_label.config(font=("Segoe UI", 9, "bold"))
    priority_label.grid(row=2, column=0, padx=5)

    priority_var = tk.StringVar(value=default_priority)
    priority_menu_choices = [default_priority] + [choice for choice in priority_choices if choice != default_priority]
    priority_menu = ttk.OptionMenu(
        assignee_frame,
        priority_var,
        default_priority,
        *priority_menu_choices,
    )
    priority_menu.grid(row=3, column=0, padx=5)

    prompt_frame = tk.Frame(root, bd=1, relief="groove")
    prompt_frame.pack(fill="x", padx=100, pady=5)

    prompt_label = tk.Label(prompt_frame, text="Custom ChatGPT Prompt:")
    prompt_label.config(font=("Segoe UI", 9, "bold"))
    prompt_label.pack()

    prompt_entry = tk.Entry(prompt_frame)
    prompt_entry.pack(fill="x", padx=5, pady=5)

    prompt_button_frame = tk.Frame(prompt_frame)
    prompt_button_frame.pack()

    include_email_checkbox_var = tk.BooleanVar()

    prompt_button = tk.Button(
        prompt_button_frame,
        text="Custom Prompt",
        command=lambda: functions.gpt.custom_prompt(
            input_text,
            prompt_entry,
            include_email_checkbox_var,
            lambda p, o: call_openai(p, o, "custom"),
            output_text,
        ),
    )
    prompt_button.grid(row=0, column=0, pady=5, padx=5)

    include_email_checkbox = tk.Checkbutton(
        prompt_button_frame,
        text="Include email for context?",
        variable=include_email_checkbox_var,
    )
    include_email_checkbox.grid(row=0, column=2, pady=5, padx=5)

    output_label.pack()

    output_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)

    root.mainloop()
