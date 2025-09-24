import os
import sqlite3
from datetime import datetime
import tkinter as tk

import functions.ui

# Database Path
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "history.db"))

# History Database
def init_history_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            mode TEXT,
            tone TEXT,
            input TEXT,
            output TEXT
        )
    ''')

def save_to_history(mode, tone, email_text, response):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cleaned_response = functions.ui.normalize_markdown_spacing(response or "")
    c.execute('''
            INSERT INTO history (timestamp, mode, tone, input, output)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), mode, tone, email_text, cleaned_response))
    conn.commit()
    conn.close()

def load_history(history_list, input_text, output_text):
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    c.execute("SELECT id, timestamp FROM history ORDER BY id DESC LIMIT 10")
    entries = c.fetchall()
    conn.close()

    history_list.menu.delete(0, "end")
    for entry_id, timestamp in entries:
        history_list.menu.add_command(
            label=f"{entry_id} - {timestamp}",
            command=lambda eid=entry_id: load_history_entry(eid, input_text, output_text)
        )

def load_history_entry(entry_id, input_text, output_text):
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    c.execute("SELECT input, output FROM history WHERE id=?", (entry_id,))
    row = c.fetchone()
    conn.close()
    if row:
        input_text.delete("1.0", tk.END)
        input_text.insert(tk.END, row[0])
        functions.ui.display_markdown(output_text, row[1] or "")
