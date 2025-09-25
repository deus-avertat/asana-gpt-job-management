import tkinter as tk


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

    prompt += "\n\nPlease respond using Markdown formatting."

    call_openai(prompt, output_text)

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
    prompt = (
        f"Draft a {draft_length} {tone.lower()} reply to this email:\n\n{email_text}\n\n"
        "Dont provide a response, subject or signature, only give the draft reply."
        " Format the reply using Markdown with headings, bullet lists, and emphasis where appropriate."
    )
    call_openai(prompt, output_text)

def summarize(input_text: str,
              model: str,
              output_text,
              attached_file_checkbox_var,
              attached_file_path,
              extract_text_from_file,
              task_checkbox_var,
              fixes_checkbox_var,
              call_openai):
    print(f"INFO: Summarizing Email using {model}")
    email_text = input_text
    if not email_text:
        return
    document_text = ""
    if attached_file_checkbox_var.get() and attached_file_path:
        document_text = extract_text_from_file(attached_file_path)
        print("INFO: Appending attached document content")

    prompt = (
        f"Summarize the following message:\n\n{email_text}\n\n"
        "Present the summary as Markdown with clear headings and bullet lists when useful.\n"
        " -Markdown should not use <p>, <div> or headers. Only bold, italics, dot points, and new lines\n"
    )
    if document_text:
        prompt += f"\nAlso summarize the following document:\n\n{document_text}"
    if task_checkbox_var.get():
        prompt += "\n\nAlso generate a numbered list of tasks in reverse order to be done based on the message."
    if fixes_checkbox_var.get():
        prompt += "\n\nAlso provide a possible fix to the issue mentioned"
    call_openai(prompt, output_text)


def draft_invoice_note(input_text: str,
                       job_title: str,
                       output_text,
                       model: str,
                       call_openai):
    """Generate a GPT prompt tailored for writing invoice notes."""

    print(f"INFO: Drafting an invoice note using {model}")
    # invoice_text = input_text.get("1.0", tk.END).strip()
    if not input_text:
        return

    prompt = (
        "You will be provided with job notes to be invoiced, and your task is to summarize the job as follows:\n"
        " -Single sentence summary of the job.\n"
        " -Dated and dot point list of what was done on the job.\n"
        " -Respond using Markdown.\n"
        " -Markdown should not use <p>, <div> or headers. Only bold, italics, dot points, and new lines\n"
        "Notes should be formatted like so:\n"
        "**Invoicing notes:**\n"
        "**[Job name]**\n"
        "[Single sentence summary]\n"
        "**[Date in DD/MM/YYYY]**\n"
        "[Dotted notes]\n\n"
        f"Invoicing Notes: {job_title}\n"
        f"{input_text}"
    )
    call_openai(prompt, output_text)
