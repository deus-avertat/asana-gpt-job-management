import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from openai import OpenAIError

import functions.database
import functions.gpt
import functions.ui
from functions.files import extract_text_from_file


def create_invoice_window(root, openai_service, config, show_main_callback):
    """Build the invoice notes assistant window."""

    invoice_window = tk.Toplevel(root)
    window_title = "Invoice Notes Assistant"
    workspace = config.get("asana_workspace") if isinstance(config, dict) else None
    if workspace:
        window_title = f"{window_title} – {workspace}"
    invoice_window.title(window_title)
    invoice_window.geometry("800x960")
    invoice_window.transient(root)

    # Ensure closing the window returns the user to the main assistant
    invoice_window.protocol("WM_DELETE_WINDOW", show_main_callback)

    model_list_var = getattr(root, "shared_model_var", tk.StringVar(master=root, value="gpt-4.0"))

    # Invoice Input
    input_label = tk.Label(invoice_window, text="Paste Invoice Details Here:")
    input_label.pack()

    input_text = scrolledtext.ScrolledText(invoice_window, height=10, wrap=tk.WORD)
    input_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)

    # Invoice history
    history_frame = tk.Frame(invoice_window)
    history_frame.pack(pady=5)

    history_list = tk.Menubutton(history_frame, text="Load History", relief="groove")
    history_list.menu = tk.Menu(history_list, tearoff=0)
    history_list["menu"] = history_list.menu
    history_list.pack(side="left")

    output_text = scrolledtext.ScrolledText(invoice_window, height=10, wrap=tk.WORD)

    def refresh_history() -> None:
        functions.database.load_history(history_list, input_text, output_text)

    refresh_button = tk.Button(
        history_frame,
        text="↻",
        command=refresh_history,
    )
    refresh_button.pack(side="left", padx=5)

    button_frame_main = tk.Frame(invoice_window)
    button_frame_main.pack()

    button_frame_left = tk.Frame(button_frame_main)
    button_frame_left.grid(column=0, row=0, padx=10)
    button_frame_left_top = tk.Frame(button_frame_left, bd=1, relief="groove", pady=5)
    button_frame_left_top.pack(pady=5)
    button_frame_left_bottom = tk.Frame(button_frame_left, bd=1, relief="groove", pady=5)
    button_frame_left_bottom.pack(pady=5)

    button_frame_right = tk.Frame(button_frame_main)
    button_frame_right.grid(column=1, row=0, padx=10)
    button_frame_right_top = tk.Frame(button_frame_right, bd=1, relief="groove", pady=5)
    button_frame_right_top.pack(pady=5)
    button_frame_right_bottom = tk.Frame(button_frame_right, bd=1, relief="groove", pady=5)
    button_frame_right_bottom.pack(pady=5)

    model_label = tk.Label(button_frame_right_top, text="Model")
    model_label.grid(row=0, column=0, padx=5)
    model_list = ttk.OptionMenu(button_frame_right_top, model_list_var, model_list_var.get(), "gpt-4.0", "gpt-4.1", "gpt-5", "o4-mini")
    model_list.grid(row=0, column=1, padx=5)

    note_style_var = tk.StringVar(value="Concise")
    note_style_label = tk.Label(button_frame_right_bottom, text="Invoice Note Style:")
    note_style_label.grid(row=0, column=0, padx=5)
    note_style_menu = ttk.OptionMenu(
        button_frame_right_bottom,
        note_style_var,
        "Concise",
        "Concise",
        "Detailed",
        "Bullet point",
    )
    note_style_menu.grid(row=0, column=1, padx=5)

    include_document_var = tk.BooleanVar()
    include_tasks_var = tk.BooleanVar()
    include_followup_var = tk.BooleanVar()

    checkbox_frame = tk.Frame(button_frame_right)
    checkbox_frame.pack(pady=5)

    include_document_checkbox = tk.Checkbutton(
        checkbox_frame,
        text="Summarise attached document?",
        variable=include_document_var,
    )
    include_document_checkbox.grid(row=0, column=0, padx=5, sticky="w")

    include_tasks_checkbox = tk.Checkbutton(
        checkbox_frame,
        text="Highlight outstanding invoice actions?",
        variable=include_tasks_var,
    )
    include_tasks_checkbox.grid(row=1, column=0, padx=5, sticky="w")

    include_followup_checkbox = tk.Checkbutton(
        checkbox_frame,
        text="Include payment follow-up suggestions?",
        variable=include_followup_var,
    )
    include_followup_checkbox.grid(row=2, column=0, padx=5, sticky="w")

    prompt_frame = tk.Frame(invoice_window, bd=1, relief="groove")
    prompt_frame.pack(fill="x", padx=100, pady=5)

    prompt_label = tk.Label(prompt_frame, text="Custom Invoice Prompt:")
    prompt_label.config(font=("Segoe UI", 9, "bold"))
    prompt_label.pack()

    prompt_entry = tk.Entry(prompt_frame)
    prompt_entry.pack(fill="x", padx=5, pady=5)

    prompt_button_frame = tk.Frame(prompt_frame)
    prompt_button_frame.pack()

    include_invoice_checkbox_var = tk.BooleanVar()

    attached_file_path = None

    def call_openai(prompt: str, output_widget: tk.Text, mode: str, tone: str = "") -> None:
        try:
            reply = openai_service.generate_response(model_list_var, prompt)
            print("INFO: Saving to local history")
            functions.database.save_to_history(mode, tone, prompt, reply)
            output_widget.config(state=tk.NORMAL)
            output_widget.delete("1.0", tk.END)
            output_widget.insert(tk.END, reply)
        except OpenAIError as exc:
            messagebox.showerror("OpenAI Error", str(exc))
        except Exception as exc:  # pragma: no cover - defensive programming
            messagebox.showerror("Error", str(exc))

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

    summarize_button = tk.Button(
        button_frame_left_top,
        text="Summarise Invoice",
        command=lambda: functions.gpt.summarize(
            input_text,
            output_text,
            include_document_var,
            attached_file_path,
            extract_text_from_file,
            include_tasks_var,
            include_followup_var,
            lambda prompt, widget: call_openai(prompt, widget, "invoice-summarize", note_style_var.get()),
        ),
    )
    summarize_button.grid(row=0, column=0, padx=5)

    draft_button = tk.Button(
        button_frame_left_top,
        text="Generate Invoice Note",
        command=lambda: functions.gpt.draft_invoice_note(
            note_style_var,
            input_text,
            output_text,
            lambda prompt, widget: call_openai(prompt, widget, "invoice-note", note_style_var.get()),
        ),
    )
    draft_button.grid(row=0, column=1, padx=5)

    attach_button = tk.Button(button_frame_left_top, text="Attach Document", command=attach_file)
    attach_button.grid(row=0, column=2, padx=5)

    prompt_button = tk.Button(
        prompt_button_frame,
        text="Run Custom Prompt",
        command=lambda: functions.gpt.custom_prompt(
            input_text,
            prompt_entry,
            include_invoice_checkbox_var,
            lambda prompt, widget: call_openai(prompt, widget, "invoice-custom", note_style_var.get()),
            output_text,
        ),
    )
    prompt_button.grid(row=0, column=0, pady=5, padx=5)

    include_invoice_checkbox = tk.Checkbutton(
        prompt_button_frame,
        text="Include invoice details for context?",
        variable=include_invoice_checkbox_var,
    )
    include_invoice_checkbox.grid(row=0, column=1, pady=5, padx=5)

    copy_button = tk.Button(
        button_frame_left_bottom,
        text="Copy Output",
        command=lambda: functions.ui.copy_output(invoice_window, output_text),
    )
    copy_button.grid(row=0, column=0, padx=5)

    back_button = tk.Button(
        button_frame_left_bottom,
        text="Back to Email Assistant",
        command=show_main_callback,
    )
    back_button.grid(row=0, column=1, padx=5)

    output_label = tk.Label(invoice_window, text="Invoice Assistant Output:")
    output_label.pack()

    output_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)

    return invoice_window
