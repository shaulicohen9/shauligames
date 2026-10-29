"""
user_management.py
===================
Core logic of the system: functions for managing users and passwords.
This file has no dependency on tkinter and can be used/tested
independently of the GUI.

Fixed version:
- Single dict {username: {"salt": ..., "hash": ...}} instead of two
  parallel lists (removes the risk of index desync between users
  and passwords).
- PBKDF2-HMAC-SHA256 (200,000 iterations) instead of a single SHA-256
  round, which makes brute-force / GPU cracking far more expensive.
- Atomic file writes (write to a temp file + os.replace) so a crash
  mid-save can't corrupt the data file.
- update_user() now REQUIRES and verifies the old password before
  allowing a new password to be set. A username-only change (no new
  password) does not require the old password.
- Each user record now also carries Hangman game stats
  ("score", "games_played", "games_won"), initialized to 0 when the
  user is created. get_user_stats()/record_game_result() manage them.
"""

import hashlib
import hmac
import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_data.json")

PBKDF2_ITERATIONS = 200_000


def load_data():
    """
    Loads the users dict from the JSON data file.
    Returns a dict: {username: {"salt": <hex>, "hash": <hex>}}.
    If the file doesn't exist or is invalid, returns an empty dict.
    """
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("users", {})
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_data(users_data):
    """
    Saves the users dict to the JSON data file atomically:
    writes to a temp file first, then replaces the real file, so a
    crash mid-write can never leave a corrupted / half-written file.
    """
    tmp_file = DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump({"users": users_data}, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DATA_FILE)


def hash_password(password, salt=None):
    """
    Hashes a password with a random salt using PBKDF2-HMAC-SHA256
    (200,000 iterations). If a salt is provided, that salt is reused
    (used when verifying).
    Returns a dict: {"salt": <hex salt>, "hash": <hex hash>}.
    """
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return {"salt": salt, "hash": hashed}


def verify_password(password, stored):
    """
    Verifies a plaintext password against a stored {"salt", "hash"} dict.
    Uses a constant-time comparison to avoid timing attacks.
    Returns True/False.
    """
    if not isinstance(stored, dict):
        return False
    salt = stored.get("salt", "")
    expected_hash = stored.get("hash", "")
    if not salt or not expected_hash:
        return False
    candidate = hash_password(password, salt)["hash"]
    return hmac.compare_digest(candidate, expected_hash)


def find_username(users_data, user):
    """
    Finds the canonical stored username matching `user`, case-insensitively.
    Returns the stored username string, or None if not found.
    """
    user_lower = user.lower()
    for existing in users_data:
        if existing.lower() == user_lower:
            return existing
    return None


def add_user_to_list(users_data, user, password):
    """
    Adds a new user with a hashed password. Also initializes the
    user's Hangman game stats (score, games played, games won) to 0.
    Returns True if added successfully, False if the user already exists.
    """
    if find_username(users_data, user) is not None:
        return False
    record = hash_password(password)
    record.update({"score": 0, "games_played": 0, "games_won": 0})
    users_data[user] = record
    return True


def check_user(users_data, user):
    """
    Checks whether a user exists, case-insensitively.
    Returns True/False.
    """
    return find_username(users_data, user) is not None


def password_policy(password):
    """
    Checks that a password meets the required policy:
    - length: at least 8 characters
    - contains at least one capital letter
    - contains at least one lower letter
    Returns True if the password is valid, False otherwise.
    """
    if len(password) < 8:
        return False

    has_upper = any(char.isupper() for char in password)
    has_lower = any(char.islower() for char in password)

    return has_upper and has_lower


def check_password_to_login(users_data, user, password):
    """
    Checks if the given password matches the specific user's stored
    (hashed) password (username lookup is case-insensitive).
    Returns True/False.
    """
    username = find_username(users_data, user)
    if username is None:
        return False
    return verify_password(password, users_data[username])


def delete_user(users_data, user):
    """
    Deletes a user.
    Returns True if deleted successfully, False if the user wasn't found.
    """
    username = find_username(users_data, user)
    if username is None:
        return False
    del users_data[username]
    return True


def update_user(users_data, old_user, old_password, new_user=None, new_password=None):
    """
    Updates an existing user's username and/or password.

    SECURITY RULE: ANY update (username change, password change, or both)
    REQUIRES `old_password` to be supplied and to verify correctly against
    the currently stored password before any change is made. Without a
    correct old password, nothing is changed - not the username, not the
    password.

    Returns a tuple (success: bool, error: str | None) where error is
    one of: "user_not_found", "wrong_password", "username_taken", None.
    """
    username = find_username(users_data, old_user)
    if username is None:
        return False, "user_not_found"

    if not old_password or not verify_password(old_password, users_data[username]):
        return False, "wrong_password"

    if new_user and new_user.lower() != username.lower():
        if find_username(users_data, new_user) is not None:
            return False, "username_taken"

    record = users_data.pop(username)
    final_username = new_user if new_user else username

    if new_password:
        # Preserve existing game stats when the password changes;
        # only the salt/hash are regenerated.
        stats = {
            "score": record.get("score", 0),
            "games_played": record.get("games_played", 0),
            "games_won": record.get("games_won", 0),
        }
        record = hash_password(new_password)
        record.update(stats)

    users_data[final_username] = record
    return True, None


def get_user_stats(users_data, user):
    """
    Returns the Hangman stats for a user as a dict:
    {"score": int, "games_played": int, "games_won": int}.
    Missing fields default to 0 (for backward compatibility with
    user records created before this feature existed).
    Returns None if the user doesn't exist.
    """
    username = find_username(users_data, user)
    if username is None:
        return None
    record = users_data[username]
    return {
        "score": record.get("score", 0),
        "games_played": record.get("games_played", 0),
        "games_won": record.get("games_won", 0),
    }


def record_game_result(users_data, user, won, points_earned=0):
    """
    Records the outcome of one Hangman game for a user:
    - increments games_played
    - if won: increments games_won and adds points_earned to score
    Returns the updated stats dict, or None if the user doesn't exist.
    Does NOT save to disk - caller is responsible for calling save_data().
    """
    username = find_username(users_data, user)
    if username is None:
        return None
    record = users_data[username]
    record["games_played"] = record.get("games_played", 0) + 1
    if won:
        record["games_won"] = record.get("games_won", 0) + 1
        record["score"] = record.get("score", 0) + points_earned
    return get_user_stats(users_data, user)


def get_leaderboard(users_data):
    """
    Builds a score-comparison table across ALL users, for display in
    a leaderboard UI.

    Returns a list of dicts, one per user, sorted by score (highest
    first, ties broken by win rate):
        {
            "username": str,
            "score": int,
            "games_played": int,
            "games_won": int,
            "win_rate": int,   # percentage, 0-100, rounded
        }
    """
    leaderboard = []
    for username in users_data:
        stats = get_user_stats(users_data, username)
        games_played = stats["games_played"]
        games_won = stats["games_won"]
        win_rate = round((games_won / games_played) * 100) if games_played else 0
        leaderboard.append({
            "username": username,
            "score": stats["score"],
            "games_played": games_played,
            "games_won": games_won,
            "win_rate": win_rate,
        })

    leaderboard.sort(key=lambda entry: (entry["score"], entry["win_rate"]), reverse=True)
    return leaderboard
