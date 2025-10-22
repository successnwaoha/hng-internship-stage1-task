import hashlib
from collections import Counter

def calculate_string_properties(value: str) -> dict:
    """Calculates all required properties for a given string."""

    # 1. length
    length = len(value)

    # 2. is_palindrome (case-insensitive)
    cleaned_value = "".join(filter(str.isalnum, value)).lower()
    is_palindrome = cleaned_value == cleaned_value[::-1]

    # 3. unique_characters
    unique_characters = len(set(value))

    # 4. word_count
    word_count = len(value.split()) # Splits by whitespace by default

    # 5. sha256_hash
    sha256_hash = hashlib.sha256(value.encode('utf-8')).hexdigest()

    # 6. character_frequency_map
    character_frequency_map = dict(Counter(value))

    return {
        "length": length,
        "is_palindrome": is_palindrome,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": sha256_hash,
        "character_frequency_map": character_frequency_map,
    }

def parse_natural_language_query(query: str) -> dict:
    """
    Attempts to parse a natural language query into filter parameters.
    This is a simplified implementation for the example queries provided.
    For a robust solution, you'd need a more advanced NLP library.
    """
    query_lower = query.lower()
    filters = {}

    if "single word" in query_lower:
        filters["word_count"] = 1
    if "palindromic" in query_lower or "palindrome" in query_lower:
        filters["is_palindrome"] = True
    if "longer than" in query_lower:
        try:
            parts = query_lower.split("longer than")
            num = int("".join(filter(str.isdigit, parts[1])))
            filters["min_length"] = num + 1
        except (ValueError, IndexError):
            pass # Handle parsing error if number isn't found
    elif "shorter than" in query_lower: # Added for completeness, though not in example
        try:
            parts = query_lower.split("shorter than")
            num = int("".join(filter(str.isdigit, parts[1])))
            filters["max_length"] = num - 1
        except (ValueError, IndexError):
            pass
    if "containing" in query_lower or "contains" in query_lower:
        # Simple heuristic: find a letter after "containing the letter" or similar
        char_match = None
        if "containing the letter " in query_lower:
            idx = query_lower.find("containing the letter ") + len("containing the letter ")
            if idx < len(query_lower):
                char_match = query_lower[idx].lower()
        elif "first vowel" in query_lower:
            char_match = "a" # As per example: "palindromic strings that contain the first vowel"
        elif "letter z" in query_lower:
            char_match = "z"

        if char_match and char_match.isalpha():
            filters["contains_character"] = char_match


    # Add more parsing rules as needed based on expected queries
    return filters