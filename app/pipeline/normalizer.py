import re

def normalize_string(text: str | None, is_reference: bool = False) -> str:
    """
    Lowercases, strips excess whitespace, and removes non-alphanumeric characters.
    If is_reference is True, removes all whitespace and punctuation (e.g. REF-123 -> ref123).
    Otherwise, replaces punctuation with spaces and normalizes spaces.
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    if is_reference:
        # Remove all non-alphanumeric characters entirely
        text = re.sub(r'[^a-z0-9]', '', text)
    else:
        # Replace non-alphanumeric characters with a space
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        # Replace multiple whitespaces with a single space and strip edges
        text = re.sub(r'\s+', ' ', text).strip()
        
    return text
