import openai
from openai import OpenAIError
import random
import time


OPENAI_MAX_ATTEMPTS = 5
OPENAI_BASE_BACKOFF_SECONDS = 0.5
OPENAI_MAX_BACKOFF_SECONDS = 8.0


class OpenAIService:
    """Thin wrapper around OpenAI chat completions."""

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            return True

        message = str(exc).lower()
        return any(
            marker in message
            for marker in (
                "timeout",
                "timed out",
                "connection reset",
                "temporarily unavailable",
            )
        )

    @staticmethod
    def _compute_backoff(attempt: int) -> float:
        # Exponential backoff with bounded jitter.
        exponential_delay = min(
            OPENAI_MAX_BACKOFF_SECONDS,
            OPENAI_BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)),
        )
        jitter = random.uniform(0.0, min(1.0, exponential_delay / 2))
        return min(OPENAI_MAX_BACKOFF_SECONDS, exponential_delay + jitter)

    def generate_response(self, model_list_var: str, prompt: str) -> str:
        """Return the assistant's reply for the given prompt."""
        last_exc: Exception | None = None

        for attempt in range(1, OPENAI_MAX_ATTEMPTS + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model_list_var,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            except OpenAIError as exc:
                last_exc = exc
                is_retryable = self._is_retryable_error(exc)
                if not is_retryable or attempt >= OPENAI_MAX_ATTEMPTS:
                    print(
                        "ERR: OpenAI completion failed"
                        f" (attempt {attempt}/{OPENAI_MAX_ATTEMPTS}, retryable={is_retryable}): {exc}"
                    )
                    raise

                sleep_for = self._compute_backoff(attempt)
                print(
                    "WARN: OpenAI completion retrying"
                    f" (attempt {attempt}/{OPENAI_MAX_ATTEMPTS}) in {sleep_for:.2f}s: {exc}"
                )
                time.sleep(sleep_for)

        if last_exc is not None:
            print(
                "ERR: OpenAI completion failed after maximum retry attempts"
                f" ({OPENAI_MAX_ATTEMPTS})."
            )
            raise last_exc

        raise RuntimeError("OpenAI completion failed without an exception.")

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