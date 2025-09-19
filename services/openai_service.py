import openai
from openai import OpenAIError


class OpenAIService:
    """Thin wrapper around OpenAI chat completions."""

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    def generate_response(self, model_list_var: str, prompt: str) -> str:
        """Return the assistant's reply for the given prompt."""
        response = self.client.chat.completions.create(
            model=model_list_var,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    # def generate_response_invoice(self, model_list_var, prompt: str) -> str:
    #     response = self.client.responses.create(
    #         model=model_list_var,
    #         input=[
    #             {
    #                 "role": "system",
    #                 "content": [
    #                     {
    #                         "type": "input_text",
    #                         "text": "You will be provided with job notes to be invoiced, and your task is to summarize the job as follows:\n -Single sentence summary of the job.\n -Dated and dot point list of what was done on the job.\n\n Notes should be formatted like so:\n **[Job name]**\n[Single sentence summary]\n[Date in DD/MM/YYYY]\n[Dotted notes]"
    #                     }
    #                 ]
    #             },
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {
    #                         "type": "input_text",
    #                         "text": prompt
    #                     }
    #                 ]
    #             }
    #         ]
    #     )
    #
    #     return response.