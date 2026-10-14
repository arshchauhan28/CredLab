"""
Question Management API Endpoints.
Provides complete CRUD, status lifecycle management, and role-based filtering.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin, get_current_faculty_or_admin, get_current_user
from app.core.database import get_db
from app.models.question import (
    Question,
    QuestionDifficulty,
    QuestionExample,
    QuestionLanguage,
    QuestionStatus,
)
from app.models.submission import TestCase
from app.models.user import User, UserRole
from app.schemas.question import (
    QuestionCreate,
    QuestionListItem,
    QuestionResponse,
    QuestionStatusUpdate,
    QuestionUpdate,
    slugify,
)
from app.schemas.submission import TestCaseCreate, TestCaseResponse

router = APIRouter()



def build_question_response(question: Question) -> QuestionResponse:
    """Helper to convert Question ORM entity into QuestionResponse schema."""
    lang_names = [ql.language for ql in question.languages]
    return QuestionResponse(
        id=question.id,
        title=question.title,
        slug=question.slug,
        description=question.description,
        input_format=question.input_format,
        output_format=question.output_format,
        constraints=question.constraints,
        difficulty=question.difficulty,
        status=question.status,
        created_by=question.created_by,
        created_at=question.created_at,
        updated_at=question.updated_at,
        allowed_languages=lang_names,
        examples=question.examples,
    )


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new programming problem (Admin or Faculty)",
)
async def create_question(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_faculty_or_admin),
) -> QuestionResponse:
    """
    Creates a new question with supported languages and public sample test cases.
    Enforces unique slugs and associates the creator to the authenticated admin or faculty member.
    If a custom slug is provided, validates uniqueness and rejects duplicates with HTTP 409.
    If title produces a duplicate slug, generates a unique incremented slug (-2, -3, etc.).
    Handles concurrent requests safely with retry logic.
    """
    # 1. If custom slug is provided, validate uniqueness per API contract
    if payload.slug:
        existing = db.query(Question.id).filter(Question.slug == payload.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A question with the slug '{payload.slug}' already exists.",
            )
        resolved_slug = payload.slug
    else:
        # Auto-generate unique slug from title
        base_slug = slugify(payload.title) or "question"
        resolved_slug = base_slug
        counter = 2
        while db.query(Question.id).filter(Question.slug == resolved_slug).first():
            resolved_slug = f"{base_slug}-{counter}"
            counter += 1

    max_retries = 5
    for attempt in range(max_retries):
        try:
            # On concurrent collision retry for auto-generated slug
            if not payload.slug and attempt > 0:
                base_slug = slugify(payload.title) or "question"
                counter = 2
                while db.query(Question.id).filter(Question.slug == resolved_slug).first():
                    resolved_slug = f"{base_slug}-{counter}"
                    counter += 1

            # Create question entity
            question = Question(
                title=payload.title,
                slug=resolved_slug,
                description=payload.description,
                input_format=payload.input_format,
                output_format=payload.output_format,
                constraints=payload.constraints,
                difficulty=payload.difficulty,
                status=payload.status,
                created_by=current_user.id,  # Guaranteed server-side identity
            )
            db.add(question)
            db.flush()  # Populates question.id

            # Add allowed languages
            for lang in payload.allowed_languages:
                ql = QuestionLanguage(question_id=question.id, language=lang)
                db.add(ql)

            # Add public examples and sync authoritative test cases
            for order, ex in enumerate(payload.examples):
                disp_order = ex.display_order if ex.display_order is not None else order
                qe = QuestionExample(
                    question_id=question.id,
                    input=ex.input,
                    output=ex.output,
                    explanation=ex.explanation,
                    display_order=disp_order,
                )
                db.add(qe)
                tc = TestCase(
                    question_id=question.id,
                    input=ex.input,
                    expected_output=ex.output,
                    is_hidden=False,
                    display_order=disp_order,
                    weight=1.0,
                )
                db.add(tc)

            db.commit()
            db.refresh(question)
            return build_question_response(question)

        except IntegrityError as exc:
            db.rollback()
            # If user explicitly requested this slug or we ran out of retries
            if payload.slug or attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A question with the slug '{resolved_slug}' already exists.",
                ) from exc



@router.get(
    "",
    response_model=List[QuestionListItem],
    summary="List questions with role-based visibility",
)
async def list_questions(
    difficulty: Optional[QuestionDifficulty] = Query(None, description="Filter by difficulty"),
    status_filter: Optional[QuestionStatus] = Query(None, alias="status", description="Filter by status (Admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[QuestionListItem]:
    """
    Returns question listings.
    - Students: Strictly filtered to PUBLISHED questions only.
    - Admins: Can view all statuses or filter by specific status.
    """
    query = db.query(Question).options(
        joinedload(Question.languages),
        joinedload(Question.examples),
    )

    # Role-based visibility enforcement
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Question.status == QuestionStatus.PUBLISHED)
    else:
        if status_filter:
            query = query.filter(Question.status == status_filter)

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    questions = query.order_by(Question.created_at.desc()).all()

    items = []
    for q in questions:
        items.append(
            QuestionListItem(
                id=q.id,
                title=q.title,
                slug=q.slug,
                description=q.description,
                difficulty=q.difficulty,
                status=q.status,
                allowed_languages=[ql.language for ql in q.languages],
                example_count=len(q.examples),
                created_at=q.created_at,
            )
        )
    return items


@router.get(
    "/{question_id_or_slug}",
    response_model=QuestionResponse,
    summary="Get question details by ID or Slug",
)
async def get_question(
    question_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuestionResponse:
    """
    Retrieves full question details with allowed languages and examples.
    - Students: Can ONLY retrieve PUBLISHED questions.
    - Admins: Can retrieve DRAFT, PUBLISHED, or ARCHIVED questions.
    """
    query = db.query(Question).options(
        joinedload(Question.languages),
        joinedload(Question.examples),
    )

    if question_id_or_slug.isdigit():
        question = query.filter(Question.id == int(question_id_or_slug)).first()
    else:
        question = query.filter(Question.slug == question_id_or_slug).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    # Security check: Students cannot access unpublished questions
    if current_user.role == UserRole.STUDENT and question.status != QuestionStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    return build_question_response(question)


@router.put(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Update an existing question (Admin or Faculty)",
)
async def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_faculty_or_admin),
) -> QuestionResponse:
    """
    Updates problem content, constraints, languages, and examples.
    """
    question = (
        db.query(Question)
        .options(
            joinedload(Question.languages),
            joinedload(Question.examples),
        )
        .filter(Question.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    # Check slug uniqueness if slug is being updated
    if payload.slug and payload.slug != question.slug:
        existing = db.query(Question).filter(Question.slug == payload.slug).first()
        if existing and existing.id != question_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A question with the slug '{payload.slug}' already exists.",
            )
        question.slug = payload.slug

    # Update basic fields if provided
    if payload.title is not None:
        question.title = payload.title
    if payload.description is not None:
        question.description = payload.description
    if payload.input_format is not None:
        question.input_format = payload.input_format
    if payload.output_format is not None:
        question.output_format = payload.output_format
    if payload.constraints is not None:
        question.constraints = payload.constraints
    if payload.difficulty is not None:
        question.difficulty = payload.difficulty
    if payload.status is not None:
        question.status = payload.status

    # Synchronize allowed languages
    if payload.allowed_languages is not None:
        db.query(QuestionLanguage).filter(QuestionLanguage.question_id == question.id).delete()
        for lang in payload.allowed_languages:
            db.add(QuestionLanguage(question_id=question.id, language=lang))

    # Synchronize examples
    if payload.examples is not None:
        db.query(QuestionExample).filter(QuestionExample.question_id == question.id).delete()
        for order, ex in enumerate(payload.examples):
            db.add(
                QuestionExample(
                    question_id=question.id,
                    input=ex.input,
                    output=ex.output,
                    explanation=ex.explanation,
                    display_order=ex.display_order if ex.display_order is not None else order,
                )
            )

    db.commit()
    db.refresh(question)
    return build_question_response(question)


@router.patch(
    "/{question_id}/status",
    response_model=QuestionResponse,
    summary="Change question status (Admin or Faculty)",
)
async def update_question_status(
    question_id: int,
    payload: QuestionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_faculty_or_admin),
) -> QuestionResponse:
    """
    Changes the status of a question (DRAFT, PUBLISHED, ARCHIVED).
    """
    question = (
        db.query(Question)
        .options(
            joinedload(Question.languages),
            joinedload(Question.examples),
        )
        .filter(Question.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    question.status = payload.status
    db.commit()
    db.refresh(question)
    return build_question_response(question)


@router.delete(
    "/{question_id}",
    summary="Delete or archive a question (Admin or Faculty)",
)
async def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_faculty_or_admin),
):
    """
    Deletes a question and its associated languages and sample examples.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    db.delete(question)
    db.commit()
    return {"detail": "Question deleted successfully.", "id": question_id}


@router.post(
    "/{question_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an authoritative test case to a question (Admin or Faculty)",
)
async def create_test_case(
    question_id: int,
    payload: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> TestCaseResponse:
    """
    Creates an authoritative test case (public or hidden) for a question.
    Admin or Faculty: students cannot add or tamper with test cases.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    test_case = TestCase(
        question_id=question.id,
        input=payload.input,
        expected_output=payload.expected_output,
        is_hidden=payload.is_hidden,
        display_order=payload.display_order,
        weight=payload.weight,
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return test_case


@router.get(
    "/{question_id}/test-cases",
    response_model=List[TestCaseResponse],
    summary="List authoritative test cases for a question (Admin or Faculty)",
)
async def list_question_test_cases(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_faculty_or_admin),
) -> List[TestCaseResponse]:
    """
    Returns all authoritative test cases (including hidden cases) for a question.
    Restricted strictly to administrators and faculty to prevent test case leakage.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    return (
        db.query(TestCase)
        .filter(TestCase.question_id == question_id)
        .order_by(TestCase.display_order.asc(), TestCase.id.asc())
        .all()
    )


@router.delete(
    "/{question_id}/test-cases/{test_case_id}",
    summary="Delete an authoritative test case (Admin or Faculty)",
)
async def delete_test_case(
    question_id: int,
    test_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Deletes an authoritative test case.
    Admin or Faculty.
    """
    test_case = (
        db.query(TestCase)
        .filter(TestCase.id == test_case_id, TestCase.question_id == question_id)
        .first()
    )
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found.",
        )

    db.delete(test_case)
    db.commit()
    return {"detail": "Test case deleted successfully.", "id": test_case_id}



@router.post(
    "/{question_id}/generate-tests",
    summary="Generate additional hidden grading tests with the configured AI provider",
)
async def generate_hidden_test_cases(
    question_id: int,
    count: int = Query(6, ge=2, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_faculty_or_admin),
):
    """Generate candidate hidden cases using an OpenAI-compatible provider.

    AI output is treated as a draft test set and validated before persistence. A
    real execution engine remains the source of truth for student correctness.
    """
    import json
    import httpx
    from app.core.config import settings

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")
    if current_user.role == UserRole.FACULTY and question.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only generate tests for a problem you created.")
    if not settings.AI_API_KEY:
        raise HTTPException(status_code=503, detail="AI test generation is not configured. Add AI_API_KEY to backend/.env, or provide sample tests manually.")

    prompt = f"""Create {count} diverse, valid hidden test cases for a programming exercise. Return ONLY JSON: {{\"tests\":[{{\"input\":\"...\",\"expected_output\":\"...\"}}]}}. Use JSON string escaping for newlines. Do not include explanations or markdown. Do not invent input formats inconsistent with the statement. Include edge cases and normal cases.\nTITLE: {question.title}\nSTATEMENT: {question.description}\nINPUT FORMAT: {question.input_format or 'Not specified'}\nOUTPUT FORMAT: {question.output_format or 'Not specified'}\nCONSTRAINTS: {question.constraints or 'Not specified'}"""
    base_url = settings.AI_BASE_URL.rstrip("/")
    url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.AI_API_KEY}", "Content-Type": "application/json"},
                json={"model": settings.AI_MODEL, "temperature": 0.2, "messages": [{"role": "system", "content": "You create rigorous programming assessment test cases. Return valid JSON only."}, {"role": "user", "content": prompt}], "response_format": {"type": "json_object"}},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            cases = parsed.get("tests", [])
    except Exception:
        raise HTTPException(status_code=502, detail="The AI provider could not generate a valid test set. Check AI_BASE_URL, AI_MODEL, and API credentials.") from None

    if not isinstance(cases, list) or len(cases) < 2:
        raise HTTPException(status_code=502, detail="The AI provider returned fewer than two usable test cases.")
    cases = cases[:count]
    existing_order = db.query(TestCase).filter(TestCase.question_id == question_id).count()
    saved = 0
    for idx, item in enumerate(cases):
        if not isinstance(item, dict) or not isinstance(item.get("input"), str) or not isinstance(item.get("expected_output"), str):
            continue
        if len(item["input"]) > 16000 or len(item["expected_output"]) > 16000:
            continue
        db.add(TestCase(question_id=question_id, input=item["input"], expected_output=item["expected_output"], is_hidden=True, display_order=existing_order + idx, weight=1.0))
        saved += 1
    if saved < 2:
        db.rollback()
        raise HTTPException(status_code=502, detail="The AI provider returned invalid test-case data. No tests were saved.")
    db.commit()
    return {"question_id": question_id, "generated": saved, "hidden": True, "message": f"Saved {saved} AI-generated hidden test cases. Review the problem statement carefully before publishing."}
