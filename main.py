import json
import random
import time
from datetime import datetime
from typing import Dict, List, Union
import os
from dataclasses import dataclass, asdict
from enum import Enum

@dataclass
class Question:
    id: int
    text: str
    options: List[str]
    correct_answers: List[Union[str, int]]
    points: int
    type: str

@dataclass
class User:
    name: str
    surname: str
    attempt_count: int
    last_attempt: str

class QuizSection:
    def __init__(self, section_number: int):
        self.section_number = section_number
        self.questions = self.load_questions()
        self.current_questions = []
        self.user_answers = {}  # Changed to store {question_id: answer}
        self.score = 0

    def load_questions(self) -> List[Question]:
        file_path = f"questions/questions_section{self.section_number}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
            return [Question(**q) for q in questions_data["questions"]]

    def select_random_questions(self, count: int = 5):
        self.current_questions = random.sample(self.questions, count)

    def calculate_score(self) -> float:
        total_points = sum(q.points for q in self.current_questions)
        earned_points = 0
        
        for question in self.current_questions:
            if question.id in self.user_answers:
                user_answer = self.user_answers[question.id]
                if isinstance(user_answer, list):  # Multiple choice
                    if sorted(user_answer) == sorted(question.correct_answers):
                        earned_points += question.points
                else:  # Single choice or True/False
                    if user_answer == question.correct_answers[0]:
                        earned_points += question.points
        
        return (earned_points / total_points) * 100

class QuizManager:
    def __init__(self):
        self.sections = [QuizSection(i) for i in range(1, 5)]
        self.user = None
        self.time_limit = 600  # 10 dakika (600 saniye)
        self.start_time = None
        self.results = {}

    def register_user(self, name: str, surname: str) -> bool:
        user_data = self.load_user_data()
        user_key = f"{name.lower()}_{surname.lower()}"
        
        if user_key in user_data:
            if user_data[user_key]["attempt_count"] >= 2:
                print("You have exceeded the maximum number of attempts.")
                return False
            
            self.user = User(
                name=name,
                surname=surname,
                attempt_count=user_data[user_key]["attempt_count"] + 1,
                last_attempt=datetime.now().isoformat()
            )
        else:
            self.user = User(
                name=name,
                surname=surname,
                attempt_count=1,
                last_attempt=datetime.now().isoformat()
            )
        
        self.save_user_data()
        return True

    def load_user_data(self) -> Dict:
        try:
            with open("users/users.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_user_data(self):
        user_data = self.load_user_data()
        user_key = f"{self.user.name.lower()}_{self.user.surname.lower()}"
        user_data[user_key] = asdict(self.user)
        
        os.makedirs("users", exist_ok=True)
        with open("users/users.json", 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=4)

    def check_time_remaining(self) -> int:
        if not self.start_time:
            return self.time_limit
        elapsed_time = int(time.time() - self.start_time)
        return max(0, self.time_limit - elapsed_time)

    def present_question(self, question: Question) -> Union[str, List[str]]:
        print(f"\nSoru: {question.text}")
        
        if question.type == "true_false":
            print("1. Doğru")
            print("2. Yanlış")
            while True:
                try:
                    answer = input("Cevabınız (1 veya 2): ").strip()
                    if answer in ['1', '2']:
                        return answer
                    print("Lütfen 1 (Doğru) veya 2 (Yanlış) girin.")
                except ValueError:
                    print("Geçersiz giriş. Lütfen tekrar deneyin.")
        
        elif question.type == "single_choice":
            for i, option in enumerate(question.options, 1):
                print(f"{i}. {option}")
            while True:
                try:
                    answer = input("Cevabınız (numarayı girin): ").strip()
                    if answer.isdigit() and 1 <= int(answer) <= len(question.options):
                        return answer
                    print(f"Lütfen 1 ile {len(question.options)} arasında bir sayı girin.")
                except ValueError:
                    print("Geçersiz giriş. Lütfen tekrar deneyin.")
        
        else:  # MULTIPLE_CHOICE
            for i, option in enumerate(question.options, 1):
                print(f"{i}. {option}")
            while True:
                try:
                    answer = input("Cevaplarınız (numaraları virgülle ayırarak girin): ").strip()
                    answers = [int(a.strip()) for a in answer.split(',')]
                    if all(1 <= a <= len(question.options) for a in answers):
                        return answers
                    print(f"Lütfen 1 ile {len(question.options)} arasında geçerli sayılar girin.")
                except ValueError:
                    print("Geçersiz giriş. Lütfen tekrar deneyin.")

    def run_quiz(self):
        print("Çoklu Bölümlü Sınav Uygulamasına Hoş Geldiniz")
        name = input("Adınız: ").strip()
        surname = input("Soyadınız: ").strip()
        
        if not self.register_user(name, surname):
            return
        
        print("\nSınav Talimatları:")
        print("- Sınav 4 bölümden oluşmaktadır")
        print("- Her bölümde 5 soru bulunmaktadır")
        print("- Her bölümden geçmek için en az %75 başarı gereklidir")
        print(f"- Tüm sınavı tamamlamak için {self.time_limit} saniyeniz vardır")
        print("\nSınavı başlatmak için Enter'a basın...")
        input()
        
        self.start_time = time.time()
        
        for section in self.sections:
            section.select_random_questions()
            print(f"\n=== Bölüm {section.section_number} ===")
            
            for question in section.current_questions:
                remaining_seconds = self.check_time_remaining()
                if remaining_seconds <= 0:
                    print("\nSüre doldu!")
                    self.calculate_final_results()
                    return
                
                print(f"\nKalan süre: {remaining_seconds} saniye")
                answer = self.present_question(question)
                section.user_answers[question.id] = answer
            
            section_score = section.calculate_score()
            self.results[f"Bölüm {section.section_number}"] = section_score
            print(f"\nBölüm {section.section_number} Puanı: {section_score:.2f}%")
        
        self.calculate_final_results()

    def calculate_final_results(self):
        overall_score = sum(self.results.values()) / len(self.results)
        passed = overall_score >= 75 and all(score >= 75 for score in self.results.values())
        
        print("\n=== Final Sonuçları ===")
        for section, score in self.results.items():
            print(f"{section}: {score:.2f}%")
        print(f"\nGenel Puan: {overall_score:.2f}%")
        print(f"Final Durumu: {'GEÇTİ' if passed else 'KALDI'}")
        
        self.save_results()

    def save_results(self):
        results_data = {
            "user": asdict(self.user),
            "date": datetime.now().isoformat(),
            "results": self.results,
            "overall_score": sum(self.results.values()) / len(self.results)
        }
        
        os.makedirs("results", exist_ok=True)
        filename = f"results/{self.user.name.lower()}_{self.user.surname.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=4)

if __name__ == "__main__":
    quiz_manager = QuizManager()
    quiz_manager.run_quiz()