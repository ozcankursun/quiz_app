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
        self.time_limit = 20  # 10 minutes (600 seconds)
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
        print(f"\nQuestion: {question.text}")
        
        if question.type == "true_false":
            print("1. True")
            print("2. False")
            while True:
                try:
                    answer = input("Your answer (1 or 2): ").strip()
                    if answer in ['1', '2']:
                        return answer
                    print("Please enter 1 (True) or 2 (False).")
                except ValueError:
                    print("Invalid input. Please try again.")
        
        elif question.type == "single_choice":
            for i, option in enumerate(question.options, 1):
                print(f"{i}. {option}")
            while True:
                try:
                    answer = input("Your answer (enter number): ").strip()
                    if answer.isdigit() and 1 <= int(answer) <= len(question.options):
                        return answer
                    print(f"Please enter a number between 1 and {len(question.options)}.")
                except ValueError:
                    print("Invalid input. Please try again.")
        
        else:  # MULTIPLE_CHOICE
            for i, option in enumerate(question.options, 1):
                print(f"{i}. {option}")
            while True:
                try:
                    answer = input("Your answers (enter numbers separated by commas): ").strip()
                    answers = [int(a.strip()) for a in answer.split(',')]
                    if all(1 <= a <= len(question.options) for a in answers):
                        return answers
                    print(f"Please enter valid numbers between 1 and {len(question.options)}.")
                except ValueError:
                    print("Invalid input. Please try again.")

    def run_quiz(self):
        print("Welcome to Multi-Section Quiz Application")
        name = input("Name: ").strip()
        surname = input("Surname: ").strip()
        
        if not self.register_user(name, surname):
            return
        
        print("\nExam Instructions:")
        print("- The exam consists of 4 sections")
        print("- Each section has 5 questions")
        print("- You need at least 75% success rate to pass each section")
        print(f"- You have {self.time_limit} seconds to complete the entire exam")
        print("\nPress Enter to start the exam...")
        input()
        
        self.start_time = time.time()
        
        for section in self.sections:
            section.select_random_questions()
            print(f"\n=== Section {section.section_number} ===")
            
            for question in section.current_questions:
                remaining_seconds = self.check_time_remaining()
                if remaining_seconds <= 0:
                    print("\nTime's up!")
                    self.calculate_final_results(time_up=True)
                    return
                
                print(f"\nTime remaining: {remaining_seconds} seconds")
                answer = self.present_question(question)
                section.user_answers[question.id] = answer
            
            section_score = section.calculate_score()
            self.results[f"Section {section.section_number}"] = section_score
            print(f"\nSection {section.section_number} Score: {section_score:.2f}%")
        
        self.calculate_final_results()

    def calculate_final_results(self, time_up=False):
        if not self.results:
            print("\nTime's up! No sections were completed.")
            self.save_results(overall_score=0)  # No sections completed
            return
        
        overall_score = sum(self.results.values()) / len(self.results)
        passed = overall_score >= 75 and all(score >= 75 for score in self.results.values())
        
        print("\n=== Final Results ===")
        for section, score in self.results.items():
            print(f"{section}: {score:.2f}%")
        print(f"\nOverall Score: {overall_score:.2f}%")
        print(f"Final Status: {'PASSED' if passed else 'FAILED'}")
        
        if time_up:
            print("Note: The quiz ended because the time limit was reached.")
        
        self.save_results(overall_score)

    def save_results(self, overall_score=0):
        results_data = {
            "user": asdict(self.user),
            "date": datetime.now().isoformat(),
            "results": self.results,
            "overall_score": overall_score
        }
        
        os.makedirs("results", exist_ok=True)
        filename = f"results/{self.user.name.lower()}_{self.user.surname.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=4)


if __name__ == "__main__":
    quiz_manager = QuizManager()
    quiz_manager.run_quiz()