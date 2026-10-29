"""
hangman.py
==========
Core logic of the Hangman mini-game. No dependency on tkinter, so it
can be tested/used independently of the GUI (same design principle
as user_management.py).

The word list lives in a separate, editable JSON file (hangman_words.json)
rather than being hardcoded, so new words can be added without touching
any code.
"""

import json
import os
import random

WORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hangman_words.json")
MAX_WRONG_GUESSES = 6  # classic hangman: head, body, 2 arms, 2 legs


def load_words(path=WORDS_FILE):
    """
    Loads the word list from the JSON words file.
    Returns a list of uppercase words. Returns an empty list if the
    file is missing or invalid (caller should handle that case).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        words = data.get("words", [])
        return [w.strip().upper() for w in words if isinstance(w, str) and w.strip()]
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return []


def pick_word(words=None):
    """
    Picks a random word (a "goral" / draw) from the given word list,
    or loads the default word list if none is given.
    Raises ValueError if no words are available.
    """
    if words is None:
        words = load_words()
    if not words:
        raise ValueError("No words available to play Hangman.")
    return random.choice(words)


def new_game_state(word):
    """
    Creates a fresh game state dict for the given word.
    """
    return {
        "word": word.upper(),
        "guessed_letters": set(),
        "wrong_guesses": 0,
        "max_wrong_guesses": MAX_WRONG_GUESSES,
    }


def guess_letter(state, letter):
    """
    Applies a single letter guess to the game state (mutates it in place).
    Returns a dict describing the outcome:
      {"valid": False, "reason": "not_a_letter" | "already_guessed"}
      {"valid": True, "correct": True/False}
    """
    if not isinstance(letter, str) or len(letter) != 1 or not letter.isalpha():
        return {"valid": False, "reason": "not_a_letter"}

    letter = letter.upper()
    if letter in state["guessed_letters"]:
        return {"valid": False, "reason": "already_guessed"}

    state["guessed_letters"].add(letter)
    correct = letter in state["word"]
    if not correct:
        state["wrong_guesses"] += 1

    return {"valid": True, "correct": correct}


def get_display_word(state):
    """
    Returns the word as currently revealed, e.g. "F I _ H", with
    unguessed letters shown as underscores.
    """
    return " ".join(
        letter if letter in state["guessed_letters"] else "_"
        for letter in state["word"]
    )


def is_won(state):
    """The player has revealed every letter in the word."""
    return all(letter in state["guessed_letters"] for letter in state["word"])


def is_lost(state):
    """The player has reached the maximum number of wrong guesses."""
    return state["wrong_guesses"] >= state["max_wrong_guesses"]


def compute_score(wrong_guesses, max_wrong_guesses=MAX_WRONG_GUESSES):
    """
    Score awarded for a WIN, based on how few mistakes were made.
    A perfect game (0 wrong guesses) scores the most; every mistake
    lowers the score, with a floor of 10 points for any win at all.
    (Losses always score 0 and are handled by the caller.)
    """
    return max(10, (max_wrong_guesses - wrong_guesses + 1) * 10)


# ASCII art for each stage of the hangman, indexed by number of wrong guesses.
HANGMAN_STAGES = [
    r"""
   ------
   |    |
   |
   |
   |
   |
---------
""",
    r"""
   ------
   |    |
   |    O
   |
   |
   |
---------
""",
    r"""
   ------
   |    |
   |    O
   |    |
   |
   |
---------
""",
    r"""
   ------
   |    |
   |    O
   |   /|
   |
   |
---------
""",
    r"""
   ------
   |    |
   |    O
   |   /|\
   |
   |
---------
""",
    r"""
   ------
   |    |
   |    O
   |   /|\
   |   /
   |
---------
""",
    r"""
   ------
   |    |
   |    O
   |   /|\
   |   / \
   |
---------
""",
]
