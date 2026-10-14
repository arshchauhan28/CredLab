"""
Seed Sample Academic Practicals for University Labs.
Creates coding practicals for Lab 1 and Lab 2 with test cases and examples.
"""

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.university import Course, Lab, LabPractical, CourseEnrollment, FacultyCourseAssignment
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionExample, QuestionLanguage
from app.models.submission import TestCase

def seed():
    db = SessionLocal()
    try:
        # Check faculty and student
        faculty = db.query(User).filter(User.role == UserRole.FACULTY).first()
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()

        creator_id = faculty.id if faculty else (admin.id if admin else 1)

        # Get or create Course 1
        course = db.query(Course).first()
        if not course:
            course = Course(
                name="Python Programming & Problem Solving",
                code="CS201",
                program="B.Tech (AI & DS)",
                year_of_study="1st Year",
                semester="Semester 1",
                academic_year="2026-2027",
                description="Core university laboratory on algorithmic programming and Python problem solving.",
                is_active=True,
                created_by=creator_id,
            )
            db.add(course)
            db.commit()
            db.refresh(course)

        # Ensure student is enrolled in the course
        if student:
            enrollment = db.query(CourseEnrollment).filter(
                CourseEnrollment.student_id == student.id,
                CourseEnrollment.course_id == course.id,
            ).first()
            if not enrollment:
                db.add(CourseEnrollment(student_id=student.id, course_id=course.id, is_active=True))
                db.commit()

        # Ensure faculty is assigned to the course
        if faculty:
            assignment = db.query(FacultyCourseAssignment).filter(
                FacultyCourseAssignment.faculty_id == faculty.id,
                FacultyCourseAssignment.course_id == course.id,
            ).first()
            if not assignment:
                db.add(FacultyCourseAssignment(faculty_id=faculty.id, course_id=course.id))
                db.commit()

        # Get or create Lab 1
        lab = db.query(Lab).filter(Lab.course_id == course.id).first()
        if not lab:
            lab = Lab(
                course_id=course.id,
                title="Lab 1: Functions, Sequences & Arrays",
                description="Master core control flow, loops, and array manipulation.",
                is_published=True,
                display_order=1,
                created_by=creator_id,
            )
            db.add(lab)
            db.commit()
            db.refresh(lab)
        else:
            lab.is_published = True
            db.commit()

        # Problem 1: Fibonacci Sequence
        q1 = db.query(Question).filter(Question.slug == "generate-fibonacci-sequence").first()
        if not q1:
            q1 = Question(
                title="Generate Fibonacci Sequence",
                slug="generate-fibonacci-sequence",
                description="Write a program that takes an integer N and prints the first N numbers of the Fibonacci sequence separated by spaces.\n\nThe sequence starts with 0 and 1:\nF(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2).",
                input_format="A single integer N (1 <= N <= 30)",
                output_format="First N Fibonacci numbers separated by spaces",
                constraints="1 <= N <= 30",
                difficulty=QuestionDifficulty.EASY,
                status=QuestionStatus.PUBLISHED,
                created_by=creator_id,
            )
            db.add(q1)
            db.commit()
            db.refresh(q1)

            # Examples
            db.add(QuestionExample(question_id=q1.id, input="5", output="0 1 1 2 3", display_order=1))
            db.add(QuestionExample(question_id=q1.id, input="1", output="0", display_order=2))

            # Languages
            for lang in ["python", "cpp", "c", "java"]:
                db.add(QuestionLanguage(question_id=q1.id, language=lang))

            # Authoritative grading test cases
            db.add(TestCase(question_id=q1.id, input="5", expected_output="0 1 1 2 3", is_hidden=False, display_order=1))
            db.add(TestCase(question_id=q1.id, input="1", expected_output="0", is_hidden=False, display_order=2))
            db.add(TestCase(question_id=q1.id, input="7", expected_output="0 1 1 2 3 5 8", is_hidden=True, display_order=3))
            db.add(TestCase(question_id=q1.id, input="10", expected_output="0 1 1 2 3 5 8 13 21 34", is_hidden=True, display_order=4))
            db.commit()

        # Problem 2: Two Sum
        q2 = db.query(Question).filter(Question.slug == "two-sum-array").first()
        if not q2:
            q2 = Question(
                title="Two Sum Problem",
                slug="two-sum-array",
                description="Given an array of integers and a target sum, determine if there exist two distinct elements in the array whose sum equals the target.\n\nInput format:\nFirst line: Integer N (number of elements)\nSecond line: N space-separated integers\nThird line: Target sum T\n\nOutput:\nPrint YES if a pair exists, otherwise print NO.",
                input_format="Line 1: N\nLine 2: N space-separated integers\nLine 3: Target T",
                output_format="YES or NO",
                constraints="2 <= N <= 1000, -10^6 <= array[i], T <= 10^6",
                difficulty=QuestionDifficulty.EASY,
                status=QuestionStatus.PUBLISHED,
                created_by=creator_id,
            )
            db.add(q2)
            db.commit()
            db.refresh(q2)

            db.add(QuestionExample(question_id=q2.id, input="4\n2 7 11 15\n9", output="YES", display_order=1))
            db.add(QuestionExample(question_id=q2.id, input="3\n3 2 4\n7", output="NO", display_order=2))

            for lang in ["python", "cpp", "c", "java"]:
                db.add(QuestionLanguage(question_id=q2.id, language=lang))

            db.add(TestCase(question_id=q2.id, input="4\n2 7 11 15\n9", expected_output="YES", is_hidden=False, display_order=1))
            db.add(TestCase(question_id=q2.id, input="3\n3 2 4\n7", expected_output="NO", is_hidden=False, display_order=2))
            db.add(TestCase(question_id=q2.id, input="5\n10 20 35 50 75\n70", expected_output="YES", is_hidden=True, display_order=3))
            db.commit()

        # Problem 3: Palindrome String Checker
        q3 = db.query(Question).filter(Question.slug == "palindrome-checker").first()
        if not q3:
            q3 = Question(
                title="Palindrome String Checker",
                slug="palindrome-checker",
                description="Read a string and determine if it is a palindrome (reads the same forwards and backwards, case-sensitive).\n\nPrint TRUE if it is a palindrome, otherwise print FALSE.",
                input_format="A single non-empty string S",
                output_format="TRUE or FALSE",
                constraints="1 <= len(S) <= 500",
                difficulty=QuestionDifficulty.EASY,
                status=QuestionStatus.PUBLISHED,
                created_by=creator_id,
            )
            db.add(q3)
            db.commit()
            db.refresh(q3)

            db.add(QuestionExample(question_id=q3.id, input="radar", output="TRUE", display_order=1))
            db.add(QuestionExample(question_id=q3.id, input="hello", output="FALSE", display_order=2))

            for lang in ["python", "cpp", "c", "java"]:
                db.add(QuestionLanguage(question_id=q3.id, language=lang))

            db.add(TestCase(question_id=q3.id, input="radar", expected_output="TRUE", is_hidden=False, display_order=1))
            db.add(TestCase(question_id=q3.id, input="hello", expected_output="FALSE", is_hidden=False, display_order=2))
            db.add(TestCase(question_id=q3.id, input="racecar", expected_output="TRUE", is_hidden=True, display_order=3))
            db.commit()

        # Connect questions to LabPracticals in sequence
        # Practical 1 -> q1
        p1 = db.query(LabPractical).filter(LabPractical.lab_id == lab.id, LabPractical.sequence_number == 1).first()
        if not p1:
            p1 = LabPractical(
                lab_id=lab.id,
                question_id=q1.id,
                title="Practical 1: Fibonacci Sequence Generation",
                sequence_number=1,
                is_required=True,
                passing_threshold=100.0,
            )
            db.add(p1)
            db.commit()

        # Practical 2 -> q2
        p2 = db.query(LabPractical).filter(LabPractical.lab_id == lab.id, LabPractical.sequence_number == 2).first()
        if not p2:
            p2 = LabPractical(
                lab_id=lab.id,
                question_id=q2.id,
                title="Practical 2: Two Sum Search in Arrays",
                sequence_number=2,
                is_required=True,
                passing_threshold=100.0,
            )
            db.add(p2)
            db.commit()

        # Practical 3 -> q3
        p3 = db.query(LabPractical).filter(LabPractical.lab_id == lab.id, LabPractical.sequence_number == 3).first()
        if not p3:
            p3 = LabPractical(
                lab_id=lab.id,
                question_id=q3.id,
                title="Practical 3: Palindrome String Verification",
                sequence_number=3,
                is_required=True,
                passing_threshold=100.0,
            )
            db.add(p3)
            db.commit()

        print("Seeding completed successfully! Practicals created.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
