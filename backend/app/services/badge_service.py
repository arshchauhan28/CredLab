"""
Badge Service.

Handles automatic awarding of practical achievement badges upon successful completion.
Validates passing results, ownership, and enforces idempotency.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.badge import Badge
from app.models.university import LabPractical, Lab
from app.models.submission import Submission, SubmissionStatus


def _generate_badge_identity(practical: LabPractical) -> tuple[str, str]:
    """Generates an achievement badge title and icon based on practical/question topic."""
    title_str = getattr(practical, "effective_title", None) or getattr(practical, "title", None) or ""
    title_lower = title_str.lower()
    if getattr(practical, "question", None) and getattr(practical.question, "title", None):
        title_lower += " " + practical.question.title.lower()

    if "array" in title_lower:
        return "Array Explorer", "📊"
    elif "linked list" in title_lower or "list" in title_lower:
        return "Linked List Specialist", "🔗"
    elif "stack" in title_lower:
        return "Stack Master", "🥞"
    elif "queue" in title_lower:
        return "Queue Expert", "🚶"
    elif "binary search" in title_lower or "search" in title_lower:
        return "Search Specialist", "🔍"
    elif "tree" in title_lower:
        return "Tree Navigator", "🌳"
    elif "graph" in title_lower:
        return "Graph Architect", "🕸️"
    elif "sort" in title_lower:
        return "Sort Connoisseur", "📶"
    elif "string" in title_lower or "palindrome" in title_lower or "anagram" in title_lower:
        return "String Wizard", "🔤"
    elif "matrix" in title_lower or "grid" in title_lower:
        return "Matrix Pathfinder", "🧱"
    elif "dynamic" in title_lower or "dp" in title_lower:
        return "DP Mastermind", "🧠"
    else:
        name = getattr(practical, "effective_title", None) or getattr(practical, "title", None) or "Practical"
        return f"{name} Achiever", "🏆"


def award_badge_if_eligible(
    db: Session,
    student_id: int,
    practical: LabPractical,
    submission: Submission,
) -> Optional[Badge]:
    """
    Awards an achievement badge if the submission meets the practical's passing criteria.
    Guarantees idempotency: returns existing badge if already earned.
    """
    # 1. Verify student ownership and practical alignment
    if submission.user_id != student_id or submission.practical_id != practical.id:
        return None

    # 2. Verify passing threshold & accepted status
    threshold = practical.passing_threshold if practical.passing_threshold is not None else 100.0
    if submission.status != SubmissionStatus.ACCEPTED or submission.score < threshold:
        return None

    # 3. Check for existing badge (idempotency)
    existing = (
        db.query(Badge)
        .filter(Badge.user_id == student_id, Badge.practical_id == practical.id)
        .first()
    )
    if existing:
        return existing

    # 4. Resolve course_id and names from lab
    course_id = None
    course_name = None
    course_code = None
    if practical.lab_id:
        lab = db.query(Lab).filter(Lab.id == practical.lab_id).first()
        if lab:
            course_id = lab.course_id
            if getattr(lab, "course", None):
                course_name = lab.course.name
                course_code = lab.course.code or lab.course.name

    # 5. Generate badge metadata
    name, icon = _generate_badge_identity(practical)
    practical_display = getattr(practical, "effective_title", None) or getattr(practical, "title", None) or "Practical Challenge"

    badge = Badge(
        user_id=student_id,
        course_id=course_id,
        practical_id=practical.id,
        badge_type="PRACTICAL_COMPLETION",
        name=name,
        description=f"Successfully mastered '{practical_display}' with {submission.score:.0f}% score.",
        icon=icon,
        meta={
            "score": submission.score,
            "language": submission.language,
            "submission_id": submission.id,
            "practical_title": practical_display,
            "course_id": course_id,
            "course_name": course_name,
            "course_code": course_code,
        },
    )

    try:
        db.add(badge)
        db.commit()
        db.refresh(badge)
        return badge
    except IntegrityError:
        db.rollback()
        return (
            db.query(Badge)
            .filter(Badge.user_id == student_id, Badge.practical_id == practical.id)
            .first()
        )
