## Summary

We use Toggl and Asana for logging jobs. The way we used to do it involved a lot of copying and pasting so I made this software to streamline the process a bit as well as teach myself how the OpenAI API works.

This program lets you copy in an email and generate a summary as well as create dot-pointed tasks for the job. You can then directly send this to Asana via the Asana API and it will create a job, assign the priority, and generate sub-tasks.
It also has a seperate window built in to assist with generating job notes to go on the final invoice. Currently there is no integration with GeoOp and Xero.

This shit is a mess and probably has a lot of unmaintanable code. Some parts were vibe coded using OpenAI's Codex.

## Configuration

Copy `config.example.json` to `config.json` and fill in the required secrets. The Asana integration now reads assignee options, priority field IDs, and any default custom fields directly from this file so you can tailor the app to your workspace without editing Python code.

## Vendored dependencies

The project vendors lightweight, offline-friendly replacements for the Markdown renderer and HTML display widget the UI relies on:

* `markdown` – provides `markdown.markdown()` and `markdown.to_plain_text()` for turning model responses into HTML or plain text.
* `tkhtmlview` – exposes `HTMLScrolledText`, a `tkinter` widget capable of displaying the rendered HTML output.

Both packages live under the `vendor/` directory and are automatically added to `sys.path` at runtime.

## Building executables

The application ships with PyInstaller spec files for two different packaging
approaches:

* **Single-file executable** – `AsanaGPTAssistant.spec` matches the original
  build and bundles everything into one file that extracts to a temporary
  directory at runtime.
* **Onedir distribution** – `AsanaGPTAssistant-onedir.spec` keeps the Python
  files unpacked beside the launcher so Tcl/Tk assets can be read directly from
  disk. This variant avoids the themed dialog issues some frozen builds hit.

To create either build:

1. Ensure you have a populated `config.json` (copy `config.example.json` and
   edit the credentials) and that `history.db` exists in the project root.
2. Install the dependencies into a virtual environment: `pip install -r
   requirements.txt`.
3. Run PyInstaller with the desired spec file, for example:

   ```bash
   pyinstaller AsanaGPTAssistant-onedir.spec --noconfirm --clean
   ```

   or

   ```bash
   pyinstaller AsanaGPTAssistant.spec --noconfirm --clean
   ```

The onedir build produces a folder containing the launcher and dependencies in
`dist/AsanaGPTAssistant`. Distribute the entire folder to keep the UI dialogs
functional.

## Screenshots

**Main Window**

<img width="802" height="992" alt="image" src="https://github.com/user-attachments/assets/b93fb5aa-5ed9-47d4-a786-a45b32b68b8a" />

**Invoicing Window**

<img width="802" height="992" alt="image" src="https://github.com/user-attachments/assets/2da455d0-2d4d-4bde-ab2d-16dd76a6f01f" />

