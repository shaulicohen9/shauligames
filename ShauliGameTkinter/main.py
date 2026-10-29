"""
main.py
=======
Main program file: builds the graphical interface (tkinter) and
runs the application. Imports the logic from user_management.py.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from user_management import (
    add_user_to_list,
    check_user,
    password_policy,
    check_password_to_login,
    delete_user,
    update_user,
    load_data,
    save_data,
    get_user_stats,
    record_game_result,
    get_leaderboard,
)

import hangman

SCORE_EXPLANATION = (
    "How scoring works:\n"
    "- A WIN scores 10 points for every wrong guess you DIDN'T make.\n"
    "  Formula: (6 - wrong guesses + 1) x 10\n"
    "  * Perfect game (0 wrong guesses) = 70 points\n"
    "  * 1 wrong guess = 60 points, 2 = 50, 3 = 40, 4 = 30, 5 = 20\n"
    "- A LOSS (running out of guesses) always scores 0 points.\n"
    "- Your total Score is the sum of points from every game you've won."
)

ERROR_MESSAGES = {
    "user_not_found": "User not found",
    "wrong_password": "Old password is incorrect. Password was not changed.",
    "username_taken": "That username is already taken.",
}


class UserManagementApp:
    """GUI class"""

    def __init__(self, root):
        self.root = root
        self.users_data = load_data()  # {username: {"salt": ..., "hash": ...}}

        self.root.title("User Management")
        self.root.geometry("700x500")

        self.build_ui()
        self.refresh_list()

    # ------------------------------------------------------------
    def build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # --- Users list ---
        list_frame = ttk.LabelFrame(main, text="Users", padding=10)
        list_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.users_listbox = tk.Listbox(list_frame, height=20, exportselection=False)
        self.users_listbox.pack(fill="both", expand=True)

        # --- Actions ---
        actions_frame = ttk.LabelFrame(main, text="Actions", padding=10)
        actions_frame.pack(side="right", fill="y", padx=5, pady=5)

        ttk.Button(actions_frame, text="Add User", width=25,
                   command=self.add_user).pack(pady=4)
        ttk.Button(actions_frame, text="Check If User Exists", width=25,
                   command=self.check_user_exists).pack(pady=4)
        ttk.Button(actions_frame, text="Delete Selected User", width=25,
                   command=self.delete_selected_user).pack(pady=4)
        ttk.Button(actions_frame, text="Update Selected User", width=25,
                   command=self.update_selected_user).pack(pady=4)
        ttk.Button(actions_frame, text="Login (Check Password)", width=25,
                   command=self.login).pack(pady=4)

        ttk.Separator(actions_frame, orient="horizontal").pack(fill="x", pady=10)

        ttk.Button(actions_frame, text="Play Hangman", width=25,
                   command=self.play_hangman).pack(pady=4)
        ttk.Button(actions_frame, text="Show Hangman Score", width=25,
                   command=self.show_hangman_score).pack(pady=4)
        ttk.Button(actions_frame, text="Show Leaderboard", width=25,
                   command=self.show_leaderboard).pack(pady=4)

        ttk.Separator(actions_frame, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(actions_frame, text="Password policy:\n- at least 8 characters\n"
                                       "- at least one uppercase letter\n"
                                       "- at least one lowercase letter",
                  justify="left").pack(pady=5)

        ttk.Label(actions_frame, text="Hangman score: fewer wrong guesses\n"
                                       "= more points. See Leaderboard for\n"
                                       "the full breakdown.",
                  justify="left").pack(pady=5)

    # ------------------------------------------------------------
    def refresh_list(self):
        self.users_listbox.delete(0, tk.END)
        for user in self.users_data:
            self.users_listbox.insert(tk.END, user)

    def get_selected_user(self):
        sel = self.users_listbox.curselection()
        if not sel:
            return None
        return self.users_listbox.get(sel[0])

    def ask_string(self, title, prompt, show=None):
        """
        Wrapper around simpledialog.askstring that forces the dialog
        to appear in front of the main window instead of behind it.
        """
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(self.root.attributes, "-topmost", False)
        result = simpledialog.askstring(title, prompt, show=show, parent=self.root)
        self.root.attributes("-topmost", False)
        return result

    # ------------------------------------------------------------
    def add_user(self):
        user = self.ask_string("Add User", "Enter new username:")
        if not user:
            return
        user = user.strip()
        if not user:
            messagebox.showerror("Error", "Username cannot be empty/blank.")
            return

        password = self.ask_string("Add User", "Enter password:", show="*")
        if password is None:
            return

        if not password_policy(password):
            messagebox.showerror(
                "Invalid Password",
                "Password does not meet the policy\n"
                "(min 8 chars, at least one uppercase and one lowercase letter)."
            )
            return

        confirm = self.ask_string("Add User", "Confirm password:", show="*")
        if confirm != password:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        if add_user_to_list(self.users_data, user, password):
            save_data(self.users_data)
            self.refresh_list()
            messagebox.showinfo("Success", f"User '{user}' added successfully.")
        else:
            messagebox.showerror("Error", "User already exists")

    def check_user_exists(self):
        user = self.ask_string("Check User", "Enter username to check:")
        if not user:
            return
        exists = check_user(self.users_data, user)
        status = "exists" if exists else "does not exist"
        messagebox.showinfo("Result", f"User '{user}' {status}")

    def delete_selected_user(self):
        user = self.get_selected_user()
        if not user:
            messagebox.showinfo("Select User", "Please select a user from the list first")
            return
        if messagebox.askyesno("Confirm", f"Delete user '{user}'?"):
            if delete_user(self.users_data, user):
                save_data(self.users_data)
                self.refresh_list()
                messagebox.showinfo("Success", f"User '{user}' deleted.")
            else:
                messagebox.showerror("Error", "User not found")

    def update_selected_user(self):
        old_user = self.get_selected_user()
        if not old_user:
            messagebox.showinfo("Select User", "Please select a user from the list first")
            return

        new_user = self.ask_string(
            "Update User", "Enter new username (leave empty to keep current):"
        )
        new_password = self.ask_string(
            "Update User", "Enter new password (leave empty to keep current):", show="*"
        )

        new_user = new_user.strip() if new_user else None
        new_password = new_password.strip() if new_password else None

        if not new_user and not new_password:
            return

        if new_password and not password_policy(new_password):
            messagebox.showerror(
                "Invalid Password",
                "New password does not meet the policy. Update cancelled."
            )
            return

        # ANY change (username and/or password) requires proving you know
        # the current password first.
        old_password = self.ask_string(
            "Confirm Identity", f"Enter CURRENT password for '{old_user}':", show="*"
        )
        if not old_password:
            messagebox.showinfo("Cancelled", "Update cancelled: current password is required.")
            return

        success, error = update_user(
            self.users_data, old_user, old_password, new_user, new_password
        )
        if success:
            save_data(self.users_data)
            self.refresh_list()
            messagebox.showinfo("Success", "User updated successfully.")
        else:
            messagebox.showerror("Error", ERROR_MESSAGES.get(error, "Update failed"))

    def login(self):
        user = self.ask_string("Login", "Enter username:")
        if not user:
            return
        password = self.ask_string("Login", "Enter password to login:", show="*")
        if password is None:
            return
        if check_password_to_login(self.users_data, user, password):
            messagebox.showinfo("Login", "Login successful")
        else:
            messagebox.showerror("Login", "Login failed")

    # ------------------------------------------------------------
    def play_hangman(self):
        user = self.get_selected_user()
        if not user:
            messagebox.showinfo("Select User", "Please select a user from the list first")
            return

        try:
            word = hangman.pick_word()
        except ValueError as e:
            messagebox.showerror("Hangman", str(e))
            return

        def on_game_over(won, wrong_guesses):
            points = hangman.compute_score(wrong_guesses) if won else 0
            record_game_result(self.users_data, user, won, points)
            save_data(self.users_data)

        HangmanWindow(self.root, user, word, on_game_over)

    def show_hangman_score(self):
        user = self.get_selected_user()
        if not user:
            messagebox.showinfo("Select User", "Please select a user from the list first")
            return
        stats = get_user_stats(self.users_data, user)
        if stats is None:
            messagebox.showerror("Error", "User not found")
            return
        messagebox.showinfo(
            "Hangman Score",
            f"Player: {user}\n\n"
            f"Score: {stats['score']}\n"
            f"Games played: {stats['games_played']}\n"
            f"Games won: {stats['games_won']}\n\n"
            f"{SCORE_EXPLANATION}"
        )

    def show_leaderboard(self):
        leaderboard = get_leaderboard(self.users_data)
        if not leaderboard:
            messagebox.showinfo("Leaderboard", "No users yet - add a user first.")
            return
        LeaderboardWindow(self.root, leaderboard)


class HangmanWindow(tk.Toplevel):
    """
    A small self-contained Hangman game window for a single user.
    Calls on_game_over(won, wrong_guesses) exactly once, when the
    game ends (win or loss), so the caller can persist score/stats.
    """

    def __init__(self, parent, username, word, on_game_over):
        super().__init__(parent)
        self.title(f"Hangman - {username}")
        self.resizable(False, False)
        self.state = hangman.new_game_state(word)
        self.on_game_over = on_game_over
        self.game_over = False

        self.transient(parent)
        self.grab_set()

        self.art_label = tk.Label(self, font=("Courier", 12), justify="left")
        self.art_label.pack(padx=15, pady=(15, 5))

        self.word_label = tk.Label(self, font=("Courier", 20, "bold"))
        self.word_label.pack(pady=5)

        self.info_label = tk.Label(self, font=("Arial", 10))
        self.info_label.pack(pady=(0, 10))

        # --- On-screen letter keyboard ---
        # Each letter is a button. Once pressed, it is guessed and then
        # disabled (and visually marked) so it can never be pressed again.
        keyboard_frame = ttk.Frame(self)
        keyboard_frame.pack(pady=5, padx=15)

        self.letter_buttons = {}
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        letters_per_row = 7
        row_frame = None
        for i, letter in enumerate(letters):
            if i % letters_per_row == 0:
                row_frame = ttk.Frame(keyboard_frame)
                row_frame.pack()
            btn = tk.Button(
                row_frame,
                text=letter,
                width=3,
                font=("Arial", 11, "bold"),
                command=lambda l=letter: self.guess_from_keyboard(l),
            )
            btn.grid(row=0, column=i % letters_per_row, padx=2, pady=2)
            self.letter_buttons[letter] = btn

        self.refresh_display()
        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def guess_from_keyboard(self, letter):
        if self.game_over:
            return

        button = self.letter_buttons.get(letter)
        result = hangman.guess_letter(self.state, letter)

        if not result["valid"]:
            # Shouldn't normally happen since the button gets disabled
            # right after use, but guard anyway.
            if button is not None:
                button.config(state="disabled")
            return

        # Mark the button so it can never be pressed again, and color
        # it to show whether the guess was correct.
        if button is not None:
            color = "#8fd18f" if result["correct"] else "#e08a8a"
            button.config(state="disabled", disabledforeground="black", bg=color)

        self.refresh_display()

        if hangman.is_won(self.state):
            self.finish_game(won=True)
        elif hangman.is_lost(self.state):
            self.finish_game(won=False)

    def refresh_display(self):
        wrong = self.state["wrong_guesses"]
        self.art_label.config(text=hangman.HANGMAN_STAGES[wrong])
        self.word_label.config(text=hangman.get_display_word(self.state))
        remaining = self.state["max_wrong_guesses"] - wrong
        guessed = ", ".join(sorted(self.state["guessed_letters"])) or "-"
        self.info_label.config(
            text=f"Wrong guesses: {wrong}/{self.state['max_wrong_guesses']} "
                 f"(remaining: {remaining})\nGuessed letters: {guessed}"
        )

    def finish_game(self, won):
        self.game_over = True
        for btn in self.letter_buttons.values():
            btn.config(state="disabled")

        if won:
            points = hangman.compute_score(self.state["wrong_guesses"])
            messagebox.showinfo("You won!", f"Great job! You earned {points} points.", parent=self)
        else:
            messagebox.showinfo(
                "Game over", f"Out of guesses! The word was '{self.state['word']}'.", parent=self
            )

        self.on_game_over(won, self.state["wrong_guesses"])
        self.destroy()

    def close_window(self):
        # Closing the window mid-game counts as a loss (no free retries),
        # but only if the game hasn't already ended naturally.
        if not self.game_over:
            self.game_over = True
            self.on_game_over(False, self.state["wrong_guesses"])
        self.destroy()


class LeaderboardWindow(tk.Toplevel):
    """
    Shows a score-comparison table across all users (rank, username,
    score, games played, games won, win rate), plus an explanation
    of how the Hangman score is calculated.
    """

    def __init__(self, parent, leaderboard):
        super().__init__(parent)
        self.title("Hangman Leaderboard")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        title_label = tk.Label(self, text="Hangman Leaderboard", font=("Arial", 14, "bold"))
        title_label.pack(padx=15, pady=(15, 5))

        columns = ("rank", "username", "score", "games_played", "games_won", "win_rate")
        headers = {
            "rank": "Rank",
            "username": "Username",
            "score": "Score",
            "games_played": "Games Played",
            "games_won": "Games Won",
            "win_rate": "Win Rate",
        }
        widths = {
            "rank": 50,
            "username": 150,
            "score": 70,
            "games_played": 100,
            "games_won": 100,
            "win_rate": 80,
        }

        tree = ttk.Treeview(self, columns=columns, show="headings", height=min(12, len(leaderboard)))
        for col in columns:
            tree.heading(col, text=headers[col])
            tree.column(col, width=widths[col], anchor="center")

        for rank, entry in enumerate(leaderboard, start=1):
            tree.insert("", tk.END, values=(
                rank,
                entry["username"],
                entry["score"],
                entry["games_played"],
                entry["games_won"],
                f"{entry['win_rate']}%",
            ))

        tree.pack(padx=15, pady=5, fill="both", expand=True)

        explanation_label = tk.Label(
            self, text=SCORE_EXPLANATION, font=("Arial", 9),
            justify="left", anchor="w",
        )
        explanation_label.pack(padx=15, pady=(10, 15), fill="x")

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 15))


def main():
    root = tk.Tk()
    app = UserManagementApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
