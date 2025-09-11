# This is WIP

import tkinter as tk
from tkinter import messagebox

import speech_recognition as sr

def transcribe_prompt_from_mic(prompt_entry):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    try:
        with mic as source:
            messagebox.showinfo("Listening", "Please speak your prompt now...")
            print("INFO: Listening to audio, please speak your prompt now...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=10)

        messagebox.showinfo("Processing", "Transcribing...")
        print("INFO: Transcribing...")

        text = recognizer.recognize_vosk(audio)

        prompt_entry.delete("1.0", tk.END)
        prompt_entry.insert(tk.END, text)
    except sr.WaitTimeoutError:
        messagebox.showwarning("Timeout", "You didn't speak in time.")
    except sr.UnknownValueError:
        messagebox.showwarning("Unrecognized", "Speech not recognized.")
    except sr.RequestError as e:
        messagebox.showerror("Error", f"Speech recognition failed: {e}")