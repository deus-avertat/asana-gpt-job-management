import tkinter as tk
import threading


# Custom GPT Prompt
def custom_prompt(input_text,
                  prompt_entry,
                  include_email_checkbox_var,
                  call_openai,
                  output_text):
    print("INFO: Sending custom prompt")
    email_text = input_text.get("1.0", tk.END).strip()
    prompt = prompt_entry.get()

    if include_email_checkbox_var.get():
        prompt += f"\n\nHere is the message for context:\n{email_text}"

    threading.Thread(target=call_openai, args=(prompt, output_text)).start()

def draft_reply(tone_var,
                draft_length,
                input_text,
                output_text,
                call_openai):
    tone = tone_var.get()
    print(f"INFO: Drafting a {draft_length} {tone.lower()} Reply Email")
    email_text = input_text.get("1.0", tk.END).strip()
    if not email_text:
        return
    prompt = f"Draft a {draft_length} {tone.lower()} reply to this email:\n\n{email_text}\n\nDont provide a response, subject or signature, only give the draft reply"
    threading.Thread(target=call_openai, args=(prompt, output_text)).start()

def summarize(input_text,
              output_text,
              attached_file_checkbox_var,
              attached_file_path,
              extract_text_from_file,
              task_checkbox_var,
              fixes_checkbox_var,
              call_openai):
    print("INFO: Summarizing Email")
    email_text = input_text.get("1.0", tk.END).strip()
    if not email_text:
        return
    document_text = ""
    if attached_file_checkbox_var.get() and attached_file_path:
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
