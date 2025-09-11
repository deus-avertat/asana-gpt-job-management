import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, simpledialog, filedialog
from tkcalendar import DateEntry
import openai
from openai import OpenAIError
import os
import json
from docx import Document
import PyPDF2

# Local Packages
import functions.database
import functions.gpt
import functions.ui
import functions.asana_api

# Load Config
print("INFO: Loading Config File")
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

openai_client = openai.OpenAI(api_key=config["openai_api_key"])
asana_token = config["asana_token"]
asana_project_id = config["asana_project_id"]
asana_workspace = config["asana_workspace"]

functions.database.init_history_db()
print("INFO: Initialising History Database")

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

        print("INFO: Saving to local history")
        functions.database.save_to_history("summarize" or "draft", tone_var.get(), prompt, reply)

        output_widget.config(state=tk.NORMAL)
        output_widget.delete("1.0", tk.END)
        output_widget.insert(tk.END, reply)
    except OpenAIError as e:
        messagebox.showerror("OpenAI Error", str(e))
    except Exception as e:
        messagebox.showerror("Error", str(e))

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
        doc = Document(path)
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

# Load History Button
history_frame = tk.Frame(root)
history_frame.pack (pady=5)

history_list = tk.Menubutton(history_frame, text="Load History", relief="raised")
history_list.menu = tk.Menu(history_list, tearoff=0)
history_list["menu"] = history_list.menu
history_list.pack(side="left")

refresh_button = tk.Button(history_frame, text="↻", command=lambda: functions.database.load_history(history_list, input_text, output_text))
refresh_button.pack(side="left", padx=5)

# Button Frame
button_frame = tk.Frame(root)
button_frame.pack(pady=10)
button_frame_top = tk.Frame(button_frame, bd=1, relief="groove", pady=5)
button_frame_top.pack(pady=5)
button_frame_bottom = tk.Frame(button_frame, bd=1, relief="groove", pady=5)
button_frame_bottom.pack(pady=5)

# Buttons
summarize_button = tk.Button(button_frame_top, text="Summarise", command=lambda: functions.gpt.summarize(input_text,
                                                                                                         output_text,
                                                                                                         attached_file_checkbox_var,
                                                                                                         attached_file_path,
                                                                                                         extract_text_from_file,
                                                                                                         task_checkbox_var,
                                                                                                         fixes_checkbox_var,
                                                                                                         call_openai))
summarize_button.grid(row=0, column=0, padx=5)

draft_button = tk.Button(button_frame_top, text="Draft Reply", command=lambda: functions.gpt.draft_reply(tone_var,
                                                                                                         draft_length,
                                                                                                         input_text,
                                                                                                         output_text,
                                                                                                         call_openai))
draft_button.grid(row=0, column=1, padx=5)

attach_button = tk.Button(button_frame_top, text="Attach Document", command=attach_file)
attach_button.grid(row=0, column=2, padx=5)

copy_button = tk.Button(button_frame_bottom, text="Copy Output", command=lambda: functions.ui.copy_output(root, output_text))
copy_button.grid(row=1, column=0, padx=5)

asana_button = tk.Button(button_frame_bottom, text="Add to Asana", command=lambda: functions.asana_api.send_to_asana(output_text, input_text,
                                                                                                                     asana_workspace, asana_project_id, asana_token,
                                                                                                                     assignee_var, priority_var, cal_var))
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

prompt_button = tk.Button(prompt_button_frame, text="Custom Prompt", command=lambda: functions.gpt.custom_prompt(input_text, prompt_entry, include_email_checkbox_var, call_openai, output_text))
prompt_button.grid(row=0, column=0, pady=5, padx=5)

# WIP
# stt_button = tk.Button(prompt_button_frame, text="🎙️ Record Prompt", command=lambda: transcribe_prompt_from_mic(prompt_entry))
# stt_button.grid(row=0, column=1, pady=5, padx=5)

include_email_checkbox_var = tk.BooleanVar()
include_email_checkbox = tk.Checkbutton(prompt_button_frame, text="Include email for context?", variable=include_email_checkbox_var)
include_email_checkbox.grid(row=0, column=2, pady=5, padx=5)

# Output Text
output_label = tk.Label(root, text="ChatGPT Output:")
output_label.pack()

output_text = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD)
output_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)


root.mainloop()
