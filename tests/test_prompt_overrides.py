"""Правки промптов: подстановка, сброс и отказ от текста без обязательных полей."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dungeon.i18n as i18n  # noqa: E402
from dungeon.i18n import (  # noqa: E402
    builtin_prompt,
    normalize_prompt_overrides,
    prompt_edit_issues,
    prompt_keys,
    prompt_placeholders,
    set_prompt_overrides,
    t,
)


def _saved_overrides():
    return {"ru": dict(i18n._PROMPT_OVERRIDES["ru"]), "en": dict(i18n._PROMPT_OVERRIDES["en"])}


def _restore(saved):
    set_prompt_overrides(saved)


def test_builtin_prompts_fill_their_own_fields():
    """Встроенные тексты сами по себе подставляются без ошибки."""
    for lang in ("ru", "en"):
        for key in prompt_keys():
            text = builtin_prompt(lang, key)
            fields = prompt_placeholders(text)
            text.format(**{name: "x" for name in fields})
            assert prompt_edit_issues(lang, key, text) is None
    print("OK  встроенные промпты подставляются своими полями")


def test_override_replaces_builtin_until_reset():
    saved = _saved_overrides()
    try:
        custom = "Своя хроника.\n{old_summary}\n{history}"
        applied = set_prompt_overrides({"ru": {"prompt.summary": custom}})
        assert applied["ru"]["prompt.summary"] == custom
        assert t("ru", "prompt.summary", old_summary="было", history="стало") == (
            "Своя хроника.\nбыло\nстало"
        )
        # Английский текст этой правкой не задет
        assert t("en", "prompt.summary", old_summary="old", history="now") == builtin_prompt(
            "en", "prompt.summary"
        ).format(old_summary="old", history="now")

        set_prompt_overrides({})
        assert t("ru", "prompt.summary", old_summary="было", history="стало") == builtin_prompt(
            "ru", "prompt.summary"
        ).format(old_summary="было", history="стало")
    finally:
        _restore(saved)
    print("OK  правка перекрывает встроенный промпт и сбрасывается")


def test_empty_and_builtin_are_not_stored():
    builtin = builtin_prompt("ru", "prompt.none")
    cleaned = normalize_prompt_overrides(
        {
            "ru": {
                "prompt.none": builtin,
                "prompt.continue": "   ",
                "prompt.summary": "Своя хроника.\n{old_summary}\n{history}",
                "not.a.prompt": "лишнее",
            }
        }
    )
    assert "prompt.none" not in cleaned["ru"]
    assert "prompt.continue" not in cleaned["ru"]
    assert "not.a.prompt" not in cleaned["ru"]
    assert cleaned["ru"]["prompt.summary"].startswith("Своя хроника.")
    print("OK  пустая правка и встроенный текст в файл не попадают")


def test_missing_placeholder_is_rejected():
    issues = prompt_edit_issues("ru", "prompt.summary", "без полей")
    assert issues is not None
    assert "old_summary" in issues["missing"]
    assert "history" in issues["missing"]
    cleaned = normalize_prompt_overrides({"ru": {"prompt.summary": "без полей"}})
    assert "prompt.summary" not in cleaned["ru"]

    unknown = prompt_edit_issues("ru", "prompt.continue", "Дальше, {hint}")
    assert unknown is not None
    assert unknown["unknown"] == ["hint"]
    assert prompt_edit_issues("ru", "prompt.continue", "") is None
    print("OK  промпт без обязательного поля не принимается")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ALL PROMPT OVERRIDE TESTS PASSED")
