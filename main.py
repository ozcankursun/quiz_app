import json
import random
import time
from datetime import datetime
from typing import Dict, List, Union
import os
from dataclasses import dataclass, asdict
import bcrypt

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
    hashed_password: str
    role: str = "student"  # Varsayılan rol
    assigned_section: Union[int, None] = None
    user_class: Union[str, None] = None  # Sadece öğrenciler için
    attempt_count: int = 0
    last_attempt: str = ""

class QuizSection:
    def __init__(self, section_number: int):
        self.section_number = section_number
        self.questions = self.load_questions()
        self.current_questions = []
        self.user_answers = {}  # Stores {question_id: answer}
        self.score = 0

    def load_questions(self) -> List[Question]:
        """Load questions from the corresponding JSON file."""
        file_path = f"questions/questions_section{self.section_number}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
            return [Question(**q) for q in questions_data["questions"]]

    def select_random_questions(self, count: int = 5):
        """Randomly select questions for the section."""
        self.current_questions = random.sample(self.questions, count)

    def calculate_score(self) -> float:
        total_points = sum(q.points for q in self.current_questions)
        earned_points = 0

        for question in self.current_questions:
            if question.id in self.user_answers:
                user_answer = self.user_answers[question.id]
                
                # Eğer çoktan seçmeli ise (liste halinde cevaplar)
                if isinstance(user_answer, list):
                    if sorted(map(str, user_answer)) == sorted(map(str, question.correct_answers)):
                        earned_points += question.points

                # Eğer tek cevaplı ise (örneğin doğru-yanlış sorusu)
                elif isinstance(user_answer, str):
                    if user_answer.strip() in question.correct_answers:
                        earned_points += question.points

        return (earned_points / total_points) * 100 if total_points > 0 else 0.0


class QuizManager:
    def __init__(self):
        self.sections = [QuizSection(i) for i in range(1, 5)]
        self.user = None
        self.time_limit = 600  # Default 10 minutes
        self.start_time = None
        self.results = {}

    def signup(self) -> bool:
        """Sign up a new user."""
        name = input("Enter your first name: ").strip()
        surname = input("Enter your last name: ").strip()
        password = input("Set your password: ").strip()
        role = input("Enter role (teacher/student): ").strip().lower()

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = self.load_user_data()
        user_key = f"{name.lower()}_{surname.lower()}"

        if user_key in user_data.get("users", {}):
            print("User already exists. Please log in.")
            return False

        if role == "teacher":
            try:
                assigned_section = int(input("Enter assigned section (1-4): ").strip())
                if assigned_section not in range(1, 5):
                    raise ValueError("Invalid section number. Must be between 1 and 4.")
            except ValueError as e:
                print(e)
                return False
            new_user = User(
                name=name,
                surname=surname,
                hashed_password=hashed_password.decode('utf-8'),
                role="teacher",
                assigned_section=assigned_section
            )
        elif role == "student":
            user_class = input("Enter class (e.g., 7-A): ").strip()
            new_user = User(
                name=name,
                surname=surname,
                hashed_password=hashed_password.decode('utf-8'),
                role="student",
                assigned_section=None,
                attempt_count=0,
                last_attempt="",
                user_class=user_class
            )
        else:
            print("Invalid role.")
            return False

        if "users" not in user_data:
            user_data["users"] = {}
        user_data["users"][user_key] = asdict(new_user)

        self.user = new_user  # `self.user` bir `User` dataclass nesnesi olacak

        self.save_user_data(user_data)
        print("Signup successful!")
        return True

    def signin(self) -> bool:
        """Sign in an existing user."""
        name = input("Enter your first name: ").strip()
        surname = input("Enter your last name: ").strip()
        password = input("Enter your password: ").strip()

        user_data = self.load_user_data()
        user_key = f"{name.lower()}_{surname.lower()}"

        if user_key not in user_data.get("users", {}):
            print("User does not exist. Please sign up.")
            return False

        user_dict = user_data["users"][user_key]
        if not bcrypt.checkpw(password.encode('utf-8'), user_dict["hashed_password"].encode('utf-8')):
            print("Incorrect password. Please try again.")
            return False

        # `self.user` değişkenini bir `User` dataclass nesnesine dönüştür
        self.user = User(
            name=user_dict["name"],
            surname=user_dict["surname"],
            hashed_password=user_dict["hashed_password"],
            attempt_count=user_dict.get("attempt_count", 0),
            last_attempt=user_dict.get("last_attempt", ""),
            role=user_dict.get("role", "student"),
            assigned_section=user_dict.get("assigned_section"),
            user_class=user_dict.get("class", None)
        )
        print(f"Login successful! Welcome {self.user.name}.")

        if self.user.role == "teacher":
            self.signin_teacher()
        elif self.user.role == "student":
            self.signin_student()
        else:
            print("Invalid role.")
            return False

        return True

    def signin_teacher(self):
        print("\nWelcome, Teacher! You can manage your assigned section.")
        while True:
            print("\n1. View Section Statistics")
            print("2. Add/Update Questions")
            print("3. Logout")
            choice = input("Choose an option: ").strip()

            if choice == "1":
                self.view_section_statistics(self.user["assigned_section"])
            elif choice == "2":
                self.add_or_update_question(self.user["assigned_section"])
            elif choice == "3":
                print("Logged out successfully.")
                break
            else:
                print("Invalid choice. Please choose again.")

    def load_user_data(self) -> Dict:
        """Load user data from a JSON file."""
        try:
            with open("users/users.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_user_data(self, user_data: Dict):
        """Save user data to a JSON file."""
        os.makedirs("users", exist_ok=True)
        with open("users/users.json", 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=4)

    def check_time_remaining(self) -> int:
        """Check remaining time for the quiz."""
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
                        return answer  # String döndürülüyor
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
                        return answer  # String döndürülüyor
                    print(f"Please enter a number between 1 and {len(question.options)}.")
                except ValueError:
                    print("Invalid input. Please try again.")
        
        else:  # MULTIPLE_CHOICE
            for i, option in enumerate(question.options, 1):
                print(f"{i}. {option}")
            while True:
                try:
                    answer = input("Your answers (enter numbers separated by commas): ").strip()
                    answers = [a.strip() for a in answer.split(',')]
                    if all(a.isdigit() and 1 <= int(a) <= len(question.options) for a in answers):
                        return answers  # Liste döndürülüyor
                    print(f"Please enter valid numbers between 1 and {len(question.options)}.")
                except ValueError:
                    print("Invalid input. Please try again.")

    def run_quiz(self):
        """Main quiz execution with signup/signin options."""
        print("Welcome to Multi-Section Quiz Application")
        print("1. Signup")
        print("2. Signin")
        choice = input("Choose an option (1 or 2): ").strip()

        if choice == "1":
            if not self.signup():
                return
        elif choice == "2":
            if not self.signin():
                return
        else:
            print("Invalid choice. Exiting.")
            return

        while True:
            # Kullanıcı giriş yaptıktan sonra seçenekler
            print("\n1. View Previous Results")
            print("2. Start New Quiz")
            print("3. Logout")
            option = input("Choose an option (1, 2, or 3): ").strip()

            if option == "1":
                self.view_previous_results()
            elif option == "2":
                self.start_new_quiz()
                break  # Sınav tamamlandığında döngüden çık
            elif option == "3":
                print("Logged out successfully. Goodbye!")
                break
            else:
                print("Invalid choice. Please choose again.")

    def view_previous_results(self):
        """Display the user's previous quiz results."""
        results_path = "results"
        user_key = f"{self.user.name.lower()}_{self.user.surname.lower()}"
        user_results = []

        if os.path.exists(results_path):
            for file_name in os.listdir(results_path):
                if file_name.startswith(user_key):
                    with open(os.path.join(results_path, file_name), 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                        user_results.append(result_data)
        
        if not user_results:
            print("\nNo previous results found.")
            return

        print("\n=== Previous Results ===")
        for result in user_results:
            print(f"Date: {result['date']}")
            print(f"Overall Score: {result['overall_score']:.2f}%")
            print(f"Section Scores: {result['results']}")
            print("Final Status:", "PASSED" if result['overall_score'] >= 75 else "FAILED")
            print("-" * 30)

    def start_new_quiz(self):
        """Start a new quiz for the logged-in user."""
        # Kullanıcı sınav hakkını kontrol et
        if self.user.attempt_count >= 2:
            print("\nYou have exceeded the maximum number of attempts. You cannot start a new quiz.")
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
            self.save_results(overall_score=0)  # Hiç bölüm tamamlanmadıysa
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
        
        # Kullanıcının sınav tarihini ve deneme sayısını güncelle
        self.user.attempt_count += 1
        self.user.last_attempt = datetime.now().isoformat()
        self.save_user_data()  # Kullanıcı bilgilerini güncelle

        os.makedirs("results", exist_ok=True)
        filename = f"results/{self.user.name.lower()}_{self.user.surname.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=4)



if __name__ == "__main__":
    quiz_manager = QuizManager()
    quiz_manager.run_quiz()
