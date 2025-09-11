import os
import tkinter as tk
from tkinter import messagebox
from docx import Document

import PyPDF2


def get_date(cal_var):
    selected_date = cal_var.get()
    print(f"INFO: Selected Date: {selected_date}")
    return selected_date

def copy_output(tk_root, output_text):
    print("INFO: Copied Output to Clipboard")
    tk_root.clipboard_clear()
    tk_root.clipboard_append(output_text.get("1.0", tk.END).strip())
    messagebox.showinfo("Copied", "Output copied to clipboard.")
