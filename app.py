from flask import Flask, request, jsonify, abort
from datetime import datetime
import hashlib
from analyzer import calculate_string_properties, parse_natural_language_query
import re # For the get_specific_string endpoint's path conversion

app = Flask(__name__)

# In-memory storage for analyzed strings
# Key: sha256_hash, Value: dict containing id, value, properties, created_at
string_store = {}

# --- Helper Function to Get a String by its SHA256 Hash ---
# This helps us convert the URL-friendly {string_value} into its hash
def get_hash_from_path_value(path_value: str):
    """
    Converts a URL-safe string representation back to its original
    and calculates its hash. This is a naive approach; for production,
    you'd likely pass the hash directly or use a URL-safe encoding.
    """
    # Simple direct hashing for the {string_value} in URL path
    # In a real app, you might want to URL-decode it first if special chars are expected
    return hashlib.sha256(path_value.encode('utf-8')).hexdigest()


# --- Endpoint 1: Create/Analyze String (POST /strings) ---
@app.route('/strings', methods=['POST'])
def create_string():
    data = request.get_json()

    # 400 Bad Request: Invalid request body or missing "value" field
    if not data:
        abort(400, description="Invalid request body")
    value = data.get("value")
    if value is None:
        abort(400, description="Missing 'value' field in request body")

    # 422 Unprocessable Entity: Invalid data type for "value" (must be string)
    if not isinstance(value, str):
        abort(422, description="'value' must be a string")

    string_properties = calculate_string_properties(value)
    string_id = string_properties["sha256_hash"]

    # 409 Conflict: String already exists in the system
    if string_id in string_store:
        abort(409, description="String already exists in the system")

    current_utc_time = datetime.utcnow().isoformat() + "Z"

    string_entry = {
        "id": string_id,
        "value": value,
        "properties": string_properties,
        "created_at": current_utc_time
    }
    string_store[string_id] = string_entry

    return jsonify(string_entry), 201 # 201 Created


# --- Endpoint 2: Get Specific String (GET /strings/{string_value}) ---
@app.route('/strings/<path:string_value>', methods=['GET'])
def get_specific_string(string_value):
    # Calculate the hash based on the raw string_value from the URL path
    # For GET, we assume string_value in URL is the actual string, not its hash.
    # We then hash it to look up in our store.
    target_hash = hashlib.sha256(string_value.encode('utf-8')).hexdigest()

    string_entry = string_store.get(target_hash)

    # 404 Not Found: String does not exist
    if not string_entry:
        abort(404, description="String does not exist in the system")

    return jsonify(string_entry), 200 # 200 OK


# --- Endpoint 3: Get All Strings with Filtering (GET /strings) ---
@app.route('/strings', methods=['GET'])
def get_all_strings():
    filtered_strings = list(string_store.values())
    filters_applied = {}

    # Query Parameters parsing and filtering
    is_palindrome = request.args.get('is_palindrome')
    min_length = request.args.get('min_length')
    max_length = request.args.get('max_length')
    word_count = request.args.get('word_count')
    contains_character = request.args.get('contains_character')

    try:
        if is_palindrome is not None:
            bool_is_palindrome = is_palindrome.lower() == 'true'
            filtered_strings = [s for s in filtered_strings if s['properties']['is_palindrome'] == bool_is_palindrome]
            filters_applied['is_palindrome'] = bool_is_palindrome

        if min_length is not None:
            int_min_length = int(min_length)
            filtered_strings = [s for s in filtered_strings if s['properties']['length'] >= int_min_length]
            filters_applied['min_length'] = int_min_length

        if max_length is not None:
            int_max_length = int(max_length)
            filtered_strings = [s for s in filtered_strings if s['properties']['length'] <= int_max_length]
            filters_applied['max_length'] = int_max_length

        if word_count is not None:
            int_word_count = int(word_count)
            filtered_strings = [s for s in filtered_strings if s['properties']['word_count'] == int_word_count]
            filters_applied['word_count'] = int_word_count

        if contains_character is not None:
            if len(contains_character) != 1:
                abort(400, description="'contains_character' must be a single character.")
            filtered_strings = [s for s in filtered_strings if contains_character in s['value']]
            filters_applied['contains_character'] = contains_character

    except ValueError:
        abort(400, description="Invalid query parameter value or type. Expected boolean or integer.")

    return jsonify({
        "data": filtered_strings,
        "count": len(filtered_strings),
        "filters_applied": filters_applied
    }), 200 # 200 OK


# --- Endpoint 4: Natural Language Filtering (GET /strings/filter-by-natural-language) ---
@app.route('/strings/filter-by-natural-language', methods=['GET'])
def natural_language_filtering():
    query = request.args.get('query')
    if not query:
        abort(400, description="Missing 'query' parameter.")

    try:
        parsed_filters = parse_natural_language_query(query)
    except Exception as e: # Catch any parsing errors from our simple parser
        abort(400, description=f"Unable to parse natural language query: {e}")

    # Check for conflicting filters (simple example: if min_length is both > X and < Y which is impossible)
    # For a simple parser, this might be less critical, but good to keep in mind.
    # For now, we'll assume the parser doesn't create conflicting filters directly.

    # Apply parsed filters to the strings
    filtered_strings = list(string_store.values())
    try:
        if 'is_palindrome' in parsed_filters:
            bool_is_palindrome = parsed_filters['is_palindrome']
            filtered_strings = [s for s in filtered_strings if s['properties']['is_palindrome'] == bool_is_palindrome]

        if 'min_length' in parsed_filters:
            int_min_length = parsed_filters['min_length']
            filtered_strings = [s for s in filtered_strings if s['properties']['length'] >= int_min_length]

        if 'max_length' in parsed_filters:
            int_max_length = parsed_filters['max_length']
            filtered_strings = [s for s in filtered_strings if s['properties']['length'] <= int_max_length]

        if 'word_count' in parsed_filters:
            int_word_count = parsed_filters['word_count']
            filtered_strings = [s for s in filtered_strings if s['properties']['word_count'] == int_word_count]

        if 'contains_character' in parsed_filters:
            char_to_find = parsed_filters['contains_character']
            filtered_strings = [s for s in filtered_strings if char_to_find in s['value'].lower()] # Case-insensitive check
            
    except Exception as e:
        abort(422, description=f"Query parsed but resulted in conflicting or unprocessable filters: {e}")


    return jsonify({
        "data": filtered_strings,
        "count": len(filtered_strings),
        "interpreted_query": {
            "original": query,
            "parsed_filters": parsed_filters
        }
    }), 200 # 200 OK


# --- Endpoint 5: Delete String (DELETE /strings/{string_value}) ---
@app.route('/strings/<path:string_value>', methods=['DELETE'])
def delete_string(string_value):
    target_hash = hashlib.sha256(string_value.encode('utf-8')).hexdigest()

    if target_hash not in string_store:
        abort(404, description="String does not exist in the system")

    del string_store[target_hash]

    return '', 204 # 204 No Content

if __name__ == '__main__':
    app.run(debug=True)