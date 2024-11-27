import json
import random
import time
from datetime import datetime
from typing import Dict, List, Union
import os
from dataclasses import dataclass, asdict
import bcrypt
from tabulate import tabulate
from dotenv import load_dotenv


# Ortam değişkenlerini .env dosyasından yükle 
load_dotenv()
# Retrieve values from environment variables
TIME_LIMIT = int(os.getenv("TIME_LIMIT", 300))  # Default to 300 seconds if not set
ATTEMPT_LIMIT = int(os.getenv("ATTEMPT_LIMIT", 3))  # Default to 3 attempts if not set
MAX_QUESTIONS_PER_SECTION = int(os.getenv("MAX_QUESTIONS_PER_SECTION", 5))  # Default to 5 questions
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Helper functions
def load_answer_keys() -> Dict:
    """Load answer keys from answers.json."""
    file_path = "answers/answers.json"
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"answers": {}}

def save_answer_keys(answer_keys: Dict):
    """Save answer keys to answers.json."""
    os.makedirs("answers", exist_ok=True)
    with open("answers/answers.json", 'w', encoding='utf-8') as f:
        json.dump(answer_keys, f, indent=4, ensure_ascii=False)


@dataclass
class Question:
    id: int
    text: str
    options: List[str]
    points: int
    type: str

@dataclass
class User:
    student_id: str  # Benzersiz kimlik numarası
    name: str
    surname: str
    hashed_password: str
    role: str = "student"
    assigned_section: Union[int, None] = None
    user_class: Union[str, None] = None
    attempt_count: int = 0
    last_attempt: str = ""

class QuizSection:
    def __init__(self, section_number: int):
        self.section_number = section_number
        self.questions = self.load_questions()
        self.current_questions = []
        self.user_answers = {}  # Stores {question_id: answer}
        self.score = 0
        self.max_questions_per_section = MAX_QUESTIONS_PER_SECTION
    
    def load_questions(self) -> List[Question]:
        """Load questions from JSON."""
        file_path = f"questions/questions_section{self.section_number}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)["questions"]
        return [Question(**question_data) for question_data in questions_data]

    def select_random_questions(self):
        """Randomly select questions for the section."""
        self.current_questions = random.sample(self.questions, self.max_questions_per_section)

    def calculate_score(self) -> float:
        answer_keys = load_answer_keys()
        section_answers = answer_keys["answers"].get(f"section{self.section_number}", {})
        total_points = sum(q.points for q in self.current_questions)
        earned_points = 0

        for question in self.current_questions:
            question_id = str(question.id)
            user_answer = self.user_answers.get(question_id, None)
            correct_answers = section_answers.get(question_id, [])

            if not user_answer:  # Yanıt verilmediyse geç
                continue

            if isinstance(user_answer, list):  # Çoktan seçmeli sorular
                correct_count = len(set(map(str, user_answer)) & set(map(str, correct_answers)))
                total_correct = len(correct_answers)

                if total_correct > 0:
                    correct_ratio = correct_count / total_correct
                    earned_points += question.points * correct_ratio

            elif isinstance(user_answer, str):  # Tek yanıtlı veya doğru/yanlış sorular
                if user_answer.strip() in map(str, correct_answers):
                    earned_points += question.points

        return (earned_points / total_points) * 100 if total_points > 0 else 0.0

    
class QuizManager:
    def __init__(self):
        self.sections = [QuizSection(i) for i in range(1, 5)]
        self.user = None
        self.time_limit = TIME_LIMIT
        self.attempt_limit = ATTEMPT_LIMIT
        self.start_time = None
        self.results = {}

    def signup(self) -> bool:
        """Sign up a new user."""
        name = input("Enter your first name: ").strip()
        surname = input("Enter your last name: ").strip()
        password = input("Set your password: ").strip()

        while True:
            role = input("Enter role (teacher/student): ").strip().lower()
            if role in ["teacher", "student"]:
                break
            else:
                print("Invalid role. Please enter 'teacher' or 'student'.")

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = self.load_user_data()

        if role == "student":
            # Sadece öğrenciler için Student ID istenir
            while True:
                try:
                    student_id = int(input("Enter your Student ID: ").strip())
                    if len(str(student_id)) in [3, 4]:  # ID uzunluğu kontrolü (3 veya 4 basamaklı olmalı)
                        break
                    else:
                        print("Invalid ID. Please enter a 3 or 4 digit Student ID.")
                except ValueError:
                    print("Invalid input. Please enter a numeric Student ID.")

            if str(student_id) in user_data.get("users", {}):
                print("Student ID already exists. Please sign in or use a different ID.")
                return False

            user_class = input("Enter class (e.g., 7-A): ").strip()
            new_user = User(
                student_id=str(student_id),
                name=name,
                surname=surname,
                hashed_password=hashed_password.decode('utf-8'),
                role="student",
                user_class=user_class
            )

        elif role == "teacher":
            # Öğretmenler için Student ID yerine Assigned Section alınır
            while True:
                try:
                    assigned_section = int(input("Enter assigned section (1-4): ").strip())
                    if 1 <= assigned_section <= 4:
                        break
                    else:
                        print("Invalid input. Please enter a number between 1 and 4.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            new_user = User(
                student_id=None,  # Öğretmenler için ID alanı boş bırakılır
                name=name,
                surname=surname,
                hashed_password=hashed_password.decode('utf-8'),
                role="teacher",
                assigned_section=assigned_section
            )

        if "users" not in user_data:
            user_data["users"] = {}

        # Kullanıcıyı kaydet
        user_key = str(student_id) if role == "student" else f"{name.lower()}_{surname.lower()}"
        user_data["users"][user_key] = asdict(new_user)

        self.user = new_user
        self.save_user_data(user_data)
        print("Signup successful!")
        return True

    def signin(self) -> bool:
        """Sign in an existing user."""
        role = input("Enter role (teacher/student): ").strip().lower()

        if role == "student":
            student_id = input("Enter your Student ID: ").strip()
            user_key = student_id
        elif role == "teacher":
            name = input("Enter your first name: ").strip()
            surname = input("Enter your last name: ").strip()
            user_key = f"{name.lower()}_{surname.lower()}"
        else:
            print("Invalid role. Please enter 'teacher' or 'student'.")
            return False

        password = input("Enter your password: ").strip()
        user_data = self.load_user_data()

        if user_key not in user_data.get("users", {}):
            print("User does not exist. Please sign up.")
            return False

        user_dict = user_data["users"][user_key]
        if not bcrypt.checkpw(password.encode('utf-8'), user_dict["hashed_password"].encode('utf-8')):
            print("Incorrect password. Please try again.")
            return False

        self.user = User(
            student_id=user_dict.get("student_id"),
            name=user_dict["name"],
            surname=user_dict["surname"],
            hashed_password=user_dict["hashed_password"],
            role=user_dict.get("role", "student"),
            assigned_section=user_dict.get("assigned_section"),
            user_class=user_dict.get("user_class"),
            attempt_count=user_dict.get("attempt_count", 0),
            last_attempt=user_dict.get("last_attempt", ""),
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


    def add_or_update_question(self, section_number: int):
        """Add or update a question and its answer key."""
        section = self.sections[section_number - 1]
        print("\n1. Add New Question")
        print("2. Update Existing Question")
        choice = input("Choose an option (1 or 2): ").strip()

        answer_keys = load_answer_keys()
        section_answers = answer_keys["answers"].setdefault(f"section{section_number}", {})

        if choice == "1":
            question_text = input("Enter the question text: ").strip()
            options = input("Enter the options (comma-separated): ").strip().split(",")
            correct_answers = input("Enter the correct answers (comma-separated): ").strip().split(",")
            points = int(input("Enter the points for the question: ").strip())
            question_type = input("Enter the question type (true_false, single_choice, multiple_choice): ").strip()

            new_question = Question(
                id=len(section.questions) + 1,
                text=question_text,
                options=options,
                points=points,
                type=question_type
            )
            section.questions.append(new_question)
            section_answers[str(new_question.id)] = correct_answers
            print("Question and answer key added successfully!")

        elif choice == "2":
            for q in section.questions:
                print(f"{q.id}. {q.text}")
            question_id = int(input("Enter the question ID to update: ").strip())
            question = next((q for q in section.questions if q.id == question_id), None)
            if not question:
                print("Invalid question ID.")
                return

            question.text = input(f"Enter the new text (current: {question.text}): ").strip() or question.text
            question.options = input(f"Enter the new options (current: {','.join(question.options)}): ").strip().split(",") or question.options
            correct_answers = input(f"Enter the new correct answers: ").strip().split(",")
            question.points = int(input(f"Enter the new points (current: {question.points}): ").strip() or question.points)

            section_answers[str(question.id)] = correct_answers
            print("Question and answer key updated successfully!")

        # Save questions to the JSON file
        self.save_questions(section_number)

        # Save the updated answer keys
        save_answer_keys(answer_keys)

    def save_questions(self, section_number: int):
        """Soruları JSON dosyasına kaydet."""
        section = self.sections[section_number - 1]
        file_path = f"questions/questions_section{section_number}.json"

        questions_data = {
            "questions": [asdict(q) for q in section.questions]
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, indent=4)
        print(f"Section {section_number} questions saved successfully!")

    def signin_student(self):
        print("\nWelcome, Student! You can participate in quizzes or view your results.")
        while True:
            print("\n1. View Previous Results")
            print("2. Start New Quiz")
            print("3. Logout")
            choice = input("Choose an option: ").strip()

            if choice == "1":
                self.view_previous_results()
            elif choice == "2":
                self.start_new_quiz()
            elif choice == "3":
                print("Logged out successfully.")
                break
            else:
                print("Invalid choice. Please choose again.")

    def signin_teacher(self):
        print("\nWelcome, Teacher! You can manage your assigned section.")
        while True:
            print("\n1. View Section Statistics")
            print("2. Add/Update Questions")
            print("3. Logout")
            choice = input("Choose an option: ").strip()

            if choice == "1":
                self.view_section_statistics(self.user.assigned_section)
            elif choice == "2":
                self.add_or_update_question(self.user.assigned_section)
            elif choice == "3":
                print("Logged out successfully.")
                break
            else:
                print("Invalid choice. Please choose again.")
    
    def view_section_statistics(self, section_number: int):
        """Display detailed statistics for the given section, including class-wise comparisons."""
        results_file = "results/results.json"

        if not os.path.exists(results_file):
            print("No results available.")
            return

        with open(results_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)

        cumulative_question_stats = {}
        cumulative_class_stats = {}

        # Aggregate data from all dates for the specified section
        for date, stats in results_data["results"].items():
            section_stats = stats["section_statistics"].get(str(section_number), {})

            # Question-based stats
            for question_id, question_data in section_stats.get("question_stats", {}).items():
                if question_id not in cumulative_question_stats:
                    cumulative_question_stats[question_id] = {"correct": 0, "incorrect": 0, "class_breakdown": {}}
                cumulative_question_stats[question_id]["correct"] += question_data.get("correct", 0)
                cumulative_question_stats[question_id]["incorrect"] += question_data.get("incorrect", 0)

                for class_name, class_data in section_stats.get("class_stats", {}).items():
                    if class_name not in cumulative_question_stats[question_id]["class_breakdown"]:
                        cumulative_question_stats[question_id]["class_breakdown"][class_name] = {"correct": 0, "incorrect": 0}
                    cumulative_question_stats[question_id]["class_breakdown"][class_name]["correct"] += class_data.get("correct", 0)
                    cumulative_question_stats[question_id]["class_breakdown"][class_name]["incorrect"] += class_data.get("incorrect", 0)

            # Class-based stats
            for class_name, class_data in section_stats.get("class_stats", {}).items():
                if class_name not in cumulative_class_stats:
                    cumulative_class_stats[class_name] = {"correct": 0, "incorrect": 0}
                cumulative_class_stats[class_name]["correct"] += class_data.get("correct", 0)
                cumulative_class_stats[class_name]["incorrect"] += class_data.get("incorrect", 0)

        # Display question-based statistics
        print("\n--- Question-Based Statistics ---")
        for question_id, stats in cumulative_question_stats.items():
            question_table = []
            print(f"\nStatistics for Question {question_id}:")

            # Class-specific stats for this question
            for class_name, class_stats in stats["class_breakdown"].items():
                total = class_stats["correct"] + class_stats["incorrect"]
                success_rate = (class_stats["correct"] / total * 100) if total > 0 else 0
                question_table.append([
                    class_name,
                    class_stats["correct"],
                    class_stats["incorrect"],
                    f"{success_rate:.2f}%",
                ])

            # Add overall totals for the question
            total_correct = stats["correct"]
            total_incorrect = stats["incorrect"]
            total_attempts = total_correct + total_incorrect
            overall_success_rate = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
            question_table.append([
                "Overall",
                total_correct,
                total_incorrect,
                f"{overall_success_rate:.2f}%",
            ])

            # Display question-specific table
            print(tabulate(question_table, headers=["Class", "Correct", "Incorrect", "Success Rate"], tablefmt="grid"))

        # Display class-based comparison
        print("\n--- Class-Based Comparison (Overall Section) ---")
        class_table = []
        for class_name, stats in cumulative_class_stats.items():
            total = stats["correct"] + stats["incorrect"]
            success_rate = (stats["correct"] / total * 100) if total > 0 else 0
            class_table.append([class_name, stats["correct"], stats["incorrect"], f"{success_rate:.2f}%"])

        print(tabulate(class_table, headers=["Class", "Correct", "Incorrect", "Success Rate"], tablefmt="grid"))


    def load_user_data(self) -> Dict:
        """Load user data from a JSON file."""
        file_path = "users/users.json"
        if not os.path.exists(file_path):
            # Dosya yoksa varsayılan yapı döndür
            return {"users": {}}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # JSON bozuksa veya dosya bulunamıyorsa varsayılan yapı döndür
            print("Warning: users.json file is empty or corrupted. Re-initializing data.")
            return {"users": {}}



    def save_user_data(self, user_data: Dict):
        """Save user data to a JSON file."""
        file_path = "users/users.json"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Klasör yoksa oluştur
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=4, ensure_ascii=False)


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
                answer = input("Your answer (1 or 2): ").strip()
                if answer in ['1', '2']:
                    return answer  # User's answer
                else:
                    print("Invalid input. Please enter 1 or 2.")

        elif question.type == "single_choice":
            for i, option in enumerate(question.options, 1):
                print(f"{i}. {option}")
            while True:
                answer = input("Your answer (enter number): ").strip()
                if answer.isdigit() and 1 <= int(answer) <= len(question.options):
                    return answer  # User's answer
                else:
                    print(f"Invalid input. Please enter a number between 1 and {len(question.options)}.")

        elif question.type == "multiple_choice":
            for i, option in enumerate(question.options, 1):
                print(f"{i}. {option}")
            while True:
                answer = input("Your answers (enter numbers separated by commas): ").strip()
                answers = [a.strip() for a in answer.split(',')]
                if all(a.isdigit() and 1 <= int(a) <= len(question.options) for a in answers):
                    return answers  # User's answers
                else:
                    print("Invalid input. Please enter valid numbers separated by commas.")

    def run_quiz(self):
        """Main quiz execution with signup/signin options."""
        while True:  # Loop until the user makes a valid choice
            print("Welcome to Multi-Section Quiz Application")
            print("1. Signup")
            print("2. Signin")
            choice = input("Choose an option (1 or 2): ").strip()

            if choice == "1":
                if self.signup():  # Proceed only if signup is successful
                    break
            elif choice == "2":
                if self.signin():  # Proceed only if signin is successful
                    break
            else:
                print("Invalid choice. Please choose a valid option.\n")

        if self.user is None:
            print("Error: User session not initialized. Exiting.")
            return

        while True:
            # Display post-login options
            print("\n1. View Previous Results")
            print("2. Start New Quiz")
            print("3. Logout")
            option = input("Choose an option (1, 2, or 3): ").strip()

            if option == "1":
                self.view_previous_results()
            elif option == "2":
                self.start_new_quiz()
                break  # Exit loop after starting the quiz
            elif option == "3":
                print("Logged out successfully. Goodbye!")
                break
            else:
                print("Invalid choice. Please choose again.\n")

    def view_previous_results(self):
        """Display the user's previous quiz results in a tabular format."""
        results_file = "results/results.json"
        if not os.path.exists(results_file):
            print("No results found.")
            return

        with open(results_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)

        student_key = f"{self.user.name.lower()}_{self.user.surname.lower()}"
        student_results = results_data.get("results", {}).get(student_key, {}).get("attempts", [])

        if not student_results:
            print("\nNo previous results found.")
            return

        for attempt in student_results:
            print(f"\n=== Attempt {attempt['attempt_id']} ({attempt['date']}) ===")
            print(f"Overall Score: {attempt['overall_score']:.2f}%")
            print(f"Status: {attempt['status']}")

            headers = ["Section", "Score", "Class Avg", "School Avg", "Comparison"]
            table_data = []

            for section, score in attempt["section_scores"].items():
                section_number = section.split()[-1]  # "Section 1" -> "1"
                section_data = results_data.get("section_statistics", {}).get(section_number, {})
                class_stats = section_data.get("class_stats", {}).get(self.user.user_class, {})
                overall_stats = section_data.get("overall", {})

                # Sınıf ortalaması
                class_total = class_stats.get("correct", 0) + class_stats.get("incorrect", 0)
                class_average = (class_stats.get("correct", 0) / class_total * 100) if class_total > 0 else 50

                # Okul ortalaması
                school_total = overall_stats.get("correct", 0) + overall_stats.get("incorrect", 0)
                school_average = (overall_stats.get("correct", 0) / school_total * 100) if school_total > 0 else 50

                # Karşılaştırma
                comparison = "Above Average" if score > class_average else "Below Average"

                table_data.append([
                    section,
                    score,
                    class_average,
                    school_average,
                    comparison
                ])

            # Tabloyu yazdır
            formatted_table_data = [
                [
                    row[0],
                    f"{row[1]:.2f}%",
                    f"{row[2]:.2f}%",
                    f"{row[3]:.2f}%",
                    row[4]
                ] for row in table_data
            ]
            print(tabulate(formatted_table_data, headers=headers, tablefmt="grid"))

            # Genel karşılaştırma
            overall_class_average = sum(row[2] for row in table_data) / len(table_data)
            overall_comparison = "Above Average" if attempt["overall_score"] > overall_class_average else "Below Average"
            print(f"\nOverall Performance: {overall_comparison} compared to class average.\n")


    def start_new_quiz(self):
        """Start a new quiz for the logged-in user."""
        # Kullanıcı sınav hakkını kontrol et
        if self.user.attempt_count >= self.attempt_limit:  # ATTEMPT_LIMIT is determined in .env file
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
        quiz_completed = False

        for section in self.sections:
            section.select_random_questions()
            print(f"\n=== Section {section.section_number} ===")

            for question in section.current_questions:
                remaining_seconds = self.check_time_remaining()
                if remaining_seconds <= 0:
                    print("\nTime's up!")
                    self.calculate_final_results(time_up=True)
                    quiz_completed = True
                    break

                print(f"\nTime remaining: {remaining_seconds} seconds")
                answer = self.present_question(question)
                section.user_answers[str(question.id)] = answer  # Cevabı kaydet

            section_score = section.calculate_score()
            self.results[f"Section {section.section_number}"] = section_score
            print(f"\nSection {section.section_number} Score: {section_score:.2f}%")

            if quiz_completed:
                break

        self.calculate_final_results()
        quiz_completed = True

        # Sınav tamamlandıysa deneme sayısını artır ve kaydet
        if quiz_completed:
            self.user.attempt_count += 1
            user_data = self.load_user_data()
            user_key = f"{self.user.name.lower()}_{self.user.surname.lower()}"
            if user_key in user_data["users"]:
                user_data["users"][user_key]["attempt_count"] = self.user.attempt_count
                user_data["users"][user_key]["last_attempt"] = datetime.now().isoformat()
                self.save_user_data(user_data)


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
        """Save the results of the quiz to results.json."""
        results_file = "results/results.json"
        if not os.path.exists("results"):
            os.makedirs("results")

        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                results_json = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            results_json = {"results": {}}

        # Öğrenciye ait anahtar
        student_key = f"{self.user.name.lower()}_{self.user.surname.lower()}"

        # Öğrencinin deneme sayısını güncelle
        user_data = results_json["results"].setdefault(student_key, {"attempts": []})
        attempt_id = len(user_data["attempts"]) + 1  # Yeni deneme için ID

        # Yeni deneme sonuçlarını kaydet
        user_data["attempts"].append({
            "attempt_id": attempt_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "section_scores": self.results,
            "overall_score": overall_score,
            "status": "PASSED" if overall_score >= 75 else "FAILED"
        })

        # Dosyayı kaydet
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_json, f, indent=4, ensure_ascii=False)

        print("Results saved successfully.")




if __name__ == "__main__":
    quiz_manager = QuizManager()
    quiz_manager.run_quiz()