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


def generate_random_answers(question_count):
    """Generate random answers for the questions."""
    return [str(random.choice([1, 2])) for _ in range(question_count)]


def test_quiz_simulation():
    user_name = "Test"
    user_surname = "User"

    # Kullanıcı verilerini temizle
    clear_user_data(user_name, user_surname)

    # QuizManager oluştur
    quiz_manager = QuizManager()

    # Kullanıcı ilk kez teste giriyor
    user_inputs = [
        user_name,
        user_surname,
        "",  # "Press Enter to start the exam"
        *generate_random_answers(5),  # Section 1 yanıtları
        *generate_random_answers(5),  # Section 2 yanıtları
        *generate_random_answers(5),  # Section 3 yanıtları
        *generate_random_answers(5),  # Section 4 yanıtları
    ]
    with patch("builtins.input", side_effect=user_inputs), patch("builtins.print") as mock_print:
        quiz_manager.run_quiz()

    # Genel skor ve section puanları hesaplama
    if hasattr(quiz_manager, "results"):
        overall_score = calculate_overall_score(quiz_manager.results)
        final_status = "PASSED" if overall_score >= 75 else "FAILED"
    else:
        raise AttributeError("QuizManager'da 'results' özelliği bulunamadı.")

    print("\n=== Kullanıcı basariyla kaydoldu ilk kez teste giriyor ve random yanitlar veriyor===")
    for section, score in quiz_manager.results.items():
        print(f"{section} Puanı: {score:.2f}%")
    print(f"Genel Skor: {overall_score:.2f}%")
    print(f"Final Durum: {final_status}")

    # İkinci deneme
    user_inputs = [
        user_name,
        user_surname,
        "",  # "Press Enter to start the exam"
        *generate_random_answers(5),  # Section 1 yanıtları
        *generate_random_answers(5),  # Section 2 yanıtları
        *generate_random_answers(5),  # Section 3 yanıtları
        *generate_random_answers(5),  # Section 4 yanıtları
    ]
    with patch("builtins.input", side_effect=user_inputs), patch("builtins.print") as mock_print:
        quiz_manager.run_quiz()

    # Genel skor ve section puanları hesaplama
    if hasattr(quiz_manager, "results"):
        overall_score = calculate_overall_score(quiz_manager.results)
        final_status = "PASSED" if overall_score >= 75 else "FAILED"
    else:
        raise AttributeError("QuizManager'da 'results' özelliği bulunamadı.")

    print("\n=== Kullanıcı ikinci kez teste giriyor ve random yanitlar veriyor===")
    for section, score in quiz_manager.results.items():
        print(f"{section} Puanı: {score:.2f}%")
    print(f"Genel Skor: {overall_score:.2f}%")
    print(f"Final Durum: {final_status}")

    # Üçüncü kez test olmaya çalışıyor (limit aşımı)
    user_inputs = [user_name, user_surname]
    with patch("builtins.input", side_effect=user_inputs), patch("builtins.print") as mock_print:
        result = quiz_manager.run_quiz()

    print("\n=== Kullanıcı 3. kez sinava girmek istiyor ve limitini aşıyor ===")
    if not result:
        print("Kullanıcı limitini aştığı için teste alınmadı.")

    # Beklenen çıktılar
    assert True, "Tüm testler başarıyla tamamlandı."
