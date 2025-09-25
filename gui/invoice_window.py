import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from vendor_setup import ensure_vendor_path

ensure_vendor_path()

from openai import OpenAIError
from tkhtmlview import HTMLScrolledText

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

    # Ensure closing the window returns the user to the main assistant
    invoice_window.protocol("WM_DELETE_WINDOW", show_main_callback)

    model_list_var = getattr(root, "shared_model_var", tk.StringVar(master=root, value="gpt-4"))

    # Job Title
    job_title_label = tk.Label(invoice_window, text="Enter Job Title:")
    job_title_label.pack()

    job_title = tk.Entry(invoice_window)
    job_title.pack(fill="x", padx=45, pady=5)

    # Invoice Input
    input_label = tk.Label(invoice_window, text="Paste Invoice Details Here:")
    input_label.pack()

    input_text = scrolledtext.ScrolledText(invoice_window, height=4, wrap=tk.WORD)
    input_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)

    output_label = tk.Label(invoice_window, text="Invoice Assistant Output:")
    output_text = HTMLScrolledText(invoice_window, height=5)

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

    model_list_label = tk.Label(button_frame_right_top, text="Select GPT Model")
    model_list_label.config(font=("Segoe UI", 9, "bold"))
    model_list_label.grid(row=0, column=0, padx=5)

    model_list = ttk.OptionMenu(button_frame_right_top, model_list_var, model_list_var.get(),
                                "gpt-4",
                                "gpt-4.1",
                                "gpt-5",
                                "o4-mini")
    model_list.grid(row=1, column=0, padx=5)

    # note_style_var = tk.StringVar(value="Concise")
    # note_style_label = tk.Label(button_frame_right_bottom, text="Invoice Note Style:")
    # note_style_label.grid(row=0, column=0, padx=5)
    # note_style_menu = ttk.OptionMenu(
    #     button_frame_right_bottom,
    #     note_style_var,
    #     "Concise",
    #     "Concise",
    #     "Detailed",
    #     "Bullet point",
    # )
    # note_style_menu.grid(row=0, column=1, padx=5)

    checkbox_frame = tk.Frame(button_frame_right)
    checkbox_frame.pack(pady=5)

    # prompt_frame = tk.Frame(invoice_window, bd=1, relief="groove")
    # prompt_frame.pack(fill="x", padx=100, pady=5)

    # prompt_label = tk.Label(prompt_frame, text="Custom Invoice Prompt:")
    # prompt_label.config(font=("Segoe UI", 9, "bold"))
    # prompt_label.pack()

    # prompt_entry = tk.Entry(prompt_frame)
    # prompt_entry.pack(fill="x", padx=5, pady=5)

    # prompt_button_frame = tk.Frame(prompt_frame)
    # prompt_button_frame.pack()

    # include_invoice_checkbox_var = tk.BooleanVar()

    run_with_loading = getattr(root, "run_with_loading", None)

    def call_openai(prompt: str, output_widget: HTMLScrolledText) -> None:
        def worker() -> None:
            try:
                reply = openai_service.generate_response(model_list_var.get(), prompt)
            except OpenAIError as exc:
                root.after(0, lambda: messagebox.showerror("OpenAI Error", str(exc)))
                return
            except Exception as exc:  # pragma: no cover - defensive programming
                root.after(0, lambda: messagebox.showerror("Error", str(exc)))
                return

            root.after(0, lambda: functions.ui.display_markdown(output_widget, reply))

        if callable(run_with_loading):
            run_with_loading("Generating response…", worker)
        else:  # pragma: no cover - fallback for unexpected embedding contexts
            threading.Thread(target=worker, daemon=True).start()

    create_notes_button = tk.Button(
        button_frame_left_top,
        text="Summarise Invoice",
        command=lambda: functions.gpt.draft_invoice_note(
            input_text.get("1.0", tk.END).strip(),
            job_title.get(),
            output_text,
            model_list_var.get(),
            lambda prompt, widget: call_openai(prompt, widget),
        ),
    )
    create_notes_button.grid(row=0, column=0, padx=5)

    # prompt_button = tk.Button(
    #     prompt_button_frame,
    #     text="Run Custom Prompt",
    #     command=lambda: functions.gpt.custom_prompt(
    #         input_text,
    #         prompt_entry,
    #         include_invoice_checkbox_var,
    #         lambda prompt, widget: call_openai(prompt, widget, "invoice-custom", note_style_var.get()),
    #         output_text,
    #     ),
    # )
    # prompt_button.grid(row=0, column=0, pady=5, padx=5)

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

    output_label.pack()

    output_text.pack(fill=tk.BOTH, padx=6, pady=5, expand=True)

    return invoice_window
