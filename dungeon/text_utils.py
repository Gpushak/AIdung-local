import re


def fix_truncated_text(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    if text[-1] in [".", "!", "?", "…", '"', "»", "*", ")", "]"]:
        return text

    punctuation_marks = [text.rfind("."), text.rfind("!"), text.rfind("?"), text.rfind("…")]
    last_pos = max(punctuation_marks)

    if last_pos != -1:
        cut_text = text[: last_pos + 1].strip()
        if text.count("*") % 2 == 0 and cut_text.count("*") % 2 != 0:
            cut_text += " *"
        if len(cut_text) > 15:
            return cut_text
    return text + "..."


def clean_dm_response(ai_text: str) -> str:
    ai_text = re.sub(r"^(Мастер|AI|Narrator|DM|ИИ|Master):\s*", "", ai_text, flags=re.IGNORECASE).strip()
    final_narration = ai_text
    final_narration = re.sub(r"\$\{?[^}]*\}?\$", "", final_narration)
    final_narration = final_narration.replace("$", "")
    final_narration = re.sub(r"[\uac00-\ud7a3\u4e00-\u9fff]", "", final_narration)
    final_narration = re.sub(r"\(\s*\)", "", final_narration).strip()
    return fix_truncated_text(final_narration)


def clean_stream_chunk(content: str) -> str:
    content = re.sub(r"[\uac00-\ud7a3\u4e00-\u9fff]", "", content)
    return content.replace("$", "").replace("{", "").replace("}", "")
