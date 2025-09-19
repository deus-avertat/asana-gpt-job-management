## Summary

We use Toggl and Asana for logging jobs. The way we used to do it involved a lot of copying and pasting so I made this software to streamline the process a bit as well as teach myself how the OpenAI API works.

This program lets you copy in an email and generate a summary as well as create dot-pointed tasks for the job. You can then directly send this to Asana via the Asana API and it will create a job, assign the priority, and generate sub-tasks.
It also has a seperate window built in to assist with generating job notes to go on the final invoice. Currently there is no integration with GeoOp and Xero.

This shit is a mess and probably has a lot of unmaintanable code. Some parts were vibe coded using OpenAI's Codex.

## Configuration

Copy `config.example.json` to `config.json` and fill in the required secrets. The Asana integration now reads assignee options, priority field IDs, and any default custom fields directly from this file so you can tailor the app to your workspace without editing Python code.

## Screenshots

**Main Window**

<img width="802" height="992" alt="image" src="https://github.com/user-attachments/assets/b93fb5aa-5ed9-47d4-a786-a45b32b68b8a" />

**Invoicing Window**

<img width="802" height="992" alt="image" src="https://github.com/user-attachments/assets/2da455d0-2d4d-4bde-ab2d-16dd76a6f01f" />

