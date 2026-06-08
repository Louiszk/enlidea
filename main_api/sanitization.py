import unicodedata
import re

# Matches the Unicode Tags Block (used for invisible steganography)
TAGS_BLOCK_RE = re.compile(r"[\U000e0000-\U000e007f]")

# Matches more than 2 consecutive combining marks (Zalgo text)
ZALGO_RE = re.compile(
    r"([\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]{2})[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]+"
)

# Matches excessive Zero-Width Joiners/Spaces and Variation Selectors.
# Allowed up to 2 consecutive invisible chars to preserve complex emoji ligatures (e.g., VS16 followed by ZWJ).
EXCESSIVE_ZWJ_RE = re.compile(r"([\u200B-\u200D\uFE0E\uFE0F\uFEFF]{2})[\u200B-\u200D\uFE0E\uFE0F\uFEFF]+")

# Matches BiDi overrides
BIDI_RE = re.compile(r"[\u202A-\u202E\u2066-\u2069]")

# Matches control characters (including null bytes and ANSI escapes)
# EXCEPT tab (\t), newline (\n), and carriage return (\r).
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def sanitize_agent_input(text: str, apply_nfkc: bool = False) -> str:
    """
    Sanitizes agent-generated text to prevent prompt injection and text-based attacks.
    """
    if not text:
        return text

    # 1. Normalize stylized text
    if apply_nfkc:
        text = unicodedata.normalize("NFKC", text)
    else:
        text = unicodedata.normalize("NFC", text)

    # 2. Strip control characters
    text = CONTROL_CHARS_RE.sub("", text)

    # 3. Strip invisible tags
    text = TAGS_BLOCK_RE.sub("", text)

    # 4. Limit combining marks and ZWJs
    text = ZALGO_RE.sub(r"\1", text)
    text = EXCESSIVE_ZWJ_RE.sub(r"\1", text)

    # 5. Remove BiDi overrides
    text = BIDI_RE.sub("", text)

    return text


def sanitize_json_payload(data, apply_nfkc: bool = False, current_depth: int = 0, max_depth: int = 100):
    """
    Recursively sanitizes lists and dictionaries with DoS protection.
    """
    if current_depth > max_depth:
        raise ValueError(f"JSON payload exceeds maximum allowed depth of {max_depth}.")

    if isinstance(data, dict):
        return {k: sanitize_json_payload(v, apply_nfkc, current_depth + 1, max_depth) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_payload(i, apply_nfkc, current_depth + 1, max_depth) for i in data]
    elif isinstance(data, str):
        return sanitize_agent_input(data, apply_nfkc)
    return data
