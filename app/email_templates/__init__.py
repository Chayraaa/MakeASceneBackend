from pathlib import Path
from html import escape


def render_email_template(template_name: str, **variables: str) -> str:
    template_path = Path(__file__).parent / template_name
    values = {key: escape(value, quote=True) for key, value in variables.items()}
    if "message" in values:
        values["message"] = values["message"].replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
    return template_path.read_text(encoding="utf-8").format(**values)
