try:
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    TOKENIZER = None


def count_tokens(text: str) -> int:
    """Возвращает количество токенов с поправкой на современные локальные модели."""
    if TOKENIZER:
        return int(len(TOKENIZER.encode(text)) / 1.65)
    return int(len(text) / 3.5)
