import pytest
import json
import os
import random
from unittest.mock import patch
from main import QuizManager


def calculate_overall_score(results):
    """Helper function to calculate the overall score from section results."""
    return sum(results.values()) / len(results)


def clear_user_data(user_name, user_surname):
    """Clear user data for the given user."""
    user_file = "users/users.json"
    if os.path.exists(user_file):
        with open(user_file, "r") as f:
            users_data = json.load(f)
        user_key = f"{user_name.lower()}_{user_surname.lower()}"
        if user_key in users_data:
            del users_data[user_key]
        with open(user_file, "w") as f:
            json.dump(users_data, f, indent=4)

def print_filtered_calls(mock_print, keywords=None):
    """Filter and print mock calls based on keywords."""
    if keywords is None:
        keywords = []
    for call in mock_print.call_args_list:
        output = call[0][0].strip()  # Remove extra spaces
        if any(keyword in output.lower() for keyword in keywords):
            print(output)

def generate_random_answers(question_count):
    """Generate random answers for the questions."""
    return [str(random.randint(1, 2)) for _ in range(question_count)]

def test_quiz_simulation():
    user_name = "Test"
    user_surname = "User"

    # Kullanıcı verilerini temizle
    clear_user_data(user_name, user_surname)

    # QuizManager oluştur
    quiz_manager = QuizManager()

    # İlk test denemesi
    user_inputs_first_attempt = [
        "1",  # Signup
        user_name,
        user_surname,
        "password123",  # Password
        "2",  # Start New Quiz
        "",  # Press Enter to start
        *generate_random_answers(5),  # Section 1
        *generate_random_answers(5),  # Section 2
        *generate_random_answers(5),  # Section 3
        *generate_random_answers(5),  # Section 4
        "3",  # Logout
    ]
    with patch("builtins.input", side_effect=user_inputs_first_attempt), patch("builtins.print") as mock_print_first:
        quiz_manager.run_quiz()
    print("\n=== Kullanıcı ilk kez teste giriyor ===")
    print_filtered_calls(mock_print_first, keywords=["score", "overall", "final status"])

    # İkinci test denemesi
    user_inputs_second_attempt = [
        "2",  # Signin
        user_name,
        user_surname,
        "password123",  # Password
        "2",  # Start New Quiz
        "",  # Press Enter to start
        *generate_random_answers(5),  # Section 1
        *generate_random_answers(5),  # Section 2
        *generate_random_answers(5),  # Section 3
        *generate_random_answers(5),  # Section 4
        "3",  # Logout
    ]
    with patch("builtins.input", side_effect=user_inputs_second_attempt), patch("builtins.print") as mock_print_second:
        quiz_manager.run_quiz()
    print("\n=== Kullanıcı ikinci kez teste giriyor ===")
    print_filtered_calls(mock_print_second, keywords=["score", "overall", "final status"])

    # Limit kontrol testi
    user_inputs_limit_check = [
        "2",  # Signin
        user_name,
        user_surname,
        "password123",  # Password
        "2",  # Start New Quiz
    ]
    with patch("builtins.input", side_effect=user_inputs_limit_check), patch("builtins.print") as mock_print_limit:
        quiz_manager.run_quiz()

    print("\n=== Kullanıcı limitini aşıyor ===")
    for call in mock_print_limit.call_args_list:
        print(f"Captured Output: {call[0][0]}")  # Print all captured output

    # Mesaj kontrolü
    expected_message = "You have exceeded the maximum number of attempts. You cannot start a new quiz."
    limit_message_found = any(expected_message.lower() in call[0][0].strip().lower() for call in mock_print_limit.call_args_list)
    print(f"Limit Message Found: {limit_message_found}")
    assert limit_message_found, f"Beklenen mesaj bulunamadı: '{expected_message}'"


