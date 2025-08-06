### ================================
### Python Standalone App: summarize_and_draft.py (Default Theme + Updated Asana Integration)
### ================================
import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, simpledialog, filedialog
from tkcalendar import DateEntry
import threading
import openai
from openai import OpenAIError
import asana
from asana.rest import ApiException
import re
import os
import json
# import docx
import PyPDF2

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

# Functions
def call_openai(prompt, output_widget):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        output_widget.config(state=tk.NORMAL)
        output_widget.delete("1.0", tk.END)
        output_widget.insert(tk.END, reply)
    except OpenAIError as e:
        messagebox.showerror("OpenAI Error", str(e))
    except Exception as e:
        messagebox.showerror("Error", str(e))

def custom_prompt():
    print("INFO: Sending custom prompt")
    email_text = input_text.get("1.0", tk.END).strip()
    prompt = prompt_entry.get()

    if include_email_checkbox_var.get():
        prompt += f"\n\nHere is the message for context:\n{email_text}"

    threading.Thread(target=call_openai, args=(prompt, output_text)).start()

def summarize():
    print("INFO: Summarizing Email")
    email_text = input_text.get("1.0", tk.END).strip()
    if not email_text:
        return
    document_text = ""
    if attached_file_checkbox_var.get and attached_file_path:
        document_text = extract_text_from_file(attached_file_path)
        print("INFO: Appending attached document content")

    prompt = f"Summarize the following message:\n\n{email_text}"
    if document_text:
        prompt += f"\nAlso summarize the following document:\n\n{document_text}"
    if task_checkbox_var.get():
        prompt += "\n\nAlso generate a list of tasks in reverse order to be done based on the message."
    if fixes_checkbox_var.get():
        prompt += "\n\nAlso provide a possible fix to the issue mentioned"
    threading.Thread(target=call_openai, args=(prompt, output_text)).start()

# def summarize_document(file_path):
#     try:
#         print("INFO: Uploading file to OpenAI")
#         uploaded_file = openai_client.files.create(
#             file=open(file_path, "rb"),
#             purpose="assistants"
#         )
#
#         print(f"INFO: File uploaded and assigned the following ID: {uploaded_file.id}")
#
#         assistant = openai_client.beta.assistants.create(
#             name="Doc Summarizer",
#             model="gpt-4-1106-preview",
#             instructions="Summarize this uploaded document in plain English.",
#             tools=[{"type": "retrieval"}],
#             file_ids=[uploaded_file.id]
#         )
#
#         thread = openai_client.beta.threads.create()
#         openai_client.beta.threads.messages.create()


def draft_reply():
    tone = tone_var.get()
    print(f"INFO: Drafting a {draft_length} {tone.lower()} Reply Email")
    email_text = input_text.get("1.0", tk.END).strip()
    if not email_text:
        return
    prompt = f"Draft a {draft_length} {tone.lower()} reply to this email:\n\n{email_text}\n\nDont provide a response, subject or signature, only give the draft reply"
    threading.Thread(target=call_openai, args=(prompt, output_text)).start()


def copy_output():
    print("INFO: Copied Output to Clipboard")
    root.clipboard_clear()
    root.clipboard_append(output_text.get("1.0", tk.END).strip())
    messagebox.showinfo("Copied", "Output copied to clipboard.")


def send_to_asana():
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
            "due_on": get_date(),
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

def get_date():
    selected_date = cal_var.get()
    print(f"INFO: Selected Date: {selected_date}")
    return selected_date

def attach_file():
    global attached_file_path
    file_path = filedialog.askopenfilename(title="Select a file to attach",
                                           filetypes=[("Text files", "*.txt"),
                                                      ("PDF files", "*.pdf"),
                                                      ("Word files", "*.docx"),
                                                      ("All files", "*.*")])
    if file_path:
        attached_file_path = file_path
        print(f"INFO: Attached file: {file_path}")

def extract_text_from_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext == ".pdf":
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        doc = docx.opendocx(path)
        return "\n".join(p.text for p in doc.paragraphs)
    return ""

# GUI Setup
root = tk.Tk()
root.title("ChatGPT Email Assistant")
root.geometry("800x960")

input_label = tk.Label(root, text="Paste Email Content Here:")
input_label.pack()

input_text = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD)
input_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)
button_frame_top = tk.Frame(button_frame, bd=1, relief="groove", pady=5)
button_frame_top.pack(pady=5)
button_frame_bottom = tk.Frame(button_frame, bd=1, relief="groove", pady=5)
button_frame_bottom.pack(pady=5)

# Buttons
summarize_button = tk.Button(button_frame_top, text="Summarise", command=summarize)
summarize_button.grid(row=0, column=0, padx=5)

draft_button = tk.Button(button_frame_top, text="Draft Reply", command=draft_reply)
draft_button.grid(row=0, column=1, padx=5)

attach_button = tk.Button(button_frame_top, text="Attach Document", command=attach_file)
attach_button.grid(row=0, column=2, padx=5)

copy_button = tk.Button(button_frame_bottom, text="Copy Output", command=copy_output)
copy_button.grid(row=1, column=0, padx=5)

asana_button = tk.Button(button_frame_bottom, text="Add to Asana", command=send_to_asana)
asana_button.grid(row=1, column=1, padx=5)

options_frame = tk.Frame(root)
options_frame.pack()

# Draft Settings
draft_frame = tk.Frame(options_frame, bd=1, relief="groove")
draft_frame.grid(row=0, column=1)

tone_label = tk.Label(draft_frame, text="Select Tone for Drafted Reply:")
tone_label.config(font=("Segoe UI", 9, "bold"))
tone_label.grid(row=0, column=1, padx=5)

tone_var = tk.StringVar(value="Professional")
tone_menu = ttk.OptionMenu(draft_frame, tone_var, "Professional", "Professional", "Semi-professional", "Casual")
tone_menu.grid(row=1, column=1, padx=5)

length_label = tk.Label(draft_frame, text="Select Length for Drafted Reply:")
length_label.config(font=("Segoe UI", 9, "bold"))
length_label.grid(row=2, column=1, padx=5)

length_var = tk.StringVar(value="Short")
length_menu = ttk.OptionMenu(draft_frame, length_var, "Short", "Short", "Medium", "Long")
length_menu.grid(row=3, column=1, padx=5)

draft_length = ""
if length_var == "Short":
    draft_length = "one to two sentence"
elif length_var == "Medium":
    draft_length = "one paragraph"
else:
    draft_length = "two paragraph"

# Checkboxes - Tasks and Fixes
checkbox_frame = tk.Frame(options_frame, bd=1, relief="groove")
checkbox_frame.grid(row=0, column=2, padx=5)

task_checkbox_var = tk.BooleanVar()
task_checkbox = tk.Checkbutton(checkbox_frame, text="Include task list in summary?", variable=task_checkbox_var)
task_checkbox.grid(row=1, column=0, padx=5)

fixes_checkbox_var = tk.BooleanVar()
fixes_checkbox = tk.Checkbutton(checkbox_frame, text="Provide possible solutions to issue?", variable=fixes_checkbox_var)
fixes_checkbox.grid(row=2, column=0, padx=5)

# Checkboxes - Attached Document
attached_file_path = None

attached_file_checkbox_var = tk.BooleanVar()
attached_file_checkbox = tk.Checkbutton(checkbox_frame, text="Summarise attached document?", variable=attached_file_checkbox_var)
attached_file_checkbox.grid(row=3, column=0, padx=5)

# Drop Down - Assignee
assignee_frame = tk.Frame(options_frame, bd=1, relief="groove")
assignee_frame.grid(row=0, column=3, padx=5)

assignee_label = tk.Label(assignee_frame, text="Assignee")
assignee_label.config(font=("Segoe UI", 9, "bold"))
assignee_label.grid(row=0, column=0, padx=5)

assignee_var = tk.StringVar(value="Tristan")
assignee_menu = ttk.OptionMenu(assignee_frame, assignee_var, "Tristan", "Tristan", "Kynan")
assignee_menu.grid(row=1, column=0, padx=5)

# Drop Down - Date
#date_frame = tk.Frame(options_frame, bd=1, relief="groove")
#date_frame.grid(row=0, column=4, padx=5)

cal_label = tk.Label(assignee_frame, text="Due Date")
cal_label.config(font=("Segoe UI", 9, "bold"))
cal_label.grid(row=0, column=1, padx=5)

cal_var = DateEntry(assignee_frame, date_pattern="yyyy-mm-dd")
cal_var.grid(row=1, column=1, padx=5)

priority_label = tk.Label(assignee_frame, text="Priority")
priority_label.config(font=("Segoe UI", 9, "bold"))
priority_label.grid(row=2, column=0, padx=5)

priority_var = tk.StringVar(value="")
priority_menu = ttk.OptionMenu(assignee_frame, priority_var, "None", "Low", "Medium", "High", "Today", "Urgent")
priority_menu.grid(row=3, column=0, padx=5)

# Custom Prompt
prompt_frame = tk.Frame(root, bd=1, relief="groove")
prompt_frame.pack(fill="x", padx=100, pady=5)

prompt_label = tk.Label(prompt_frame, text="Custom ChatGPT Prompt:")
prompt_label.config(font=("Segoe UI", 9, "bold"))
prompt_label.pack()

prompt_entry = tk.Entry(prompt_frame)
prompt_entry.pack(fill="x", padx=5, pady=5)

prompt_button_frame = tk.Frame(prompt_frame)
prompt_button_frame.pack()

prompt_button = tk.Button(prompt_button_frame, text="Custom Prompt", command=custom_prompt)
prompt_button.grid(row=0, column=0, pady=5)

include_email_checkbox_var = tk.BooleanVar()
include_email_checkbox = tk.Checkbutton(prompt_button_frame, text="Include email for context?", variable=include_email_checkbox_var)
include_email_checkbox.grid(row=0, column=1, pady=5, padx=5)

# Output Text
output_label = tk.Label(root, text="ChatGPT Output:")
output_label.pack()

output_text = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD)
output_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)


root.mainloop()
