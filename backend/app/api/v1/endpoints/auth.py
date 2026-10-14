"""
Authentication Endpoints.

Provides enrollment-authorized registration, secure login, current-user
retrieval, and student academic-profile updates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.models.authorized_enrollment import AuthorizedEnrollment
from app.models.university import Course
from app.models.registration_approval import RegistrationApproval
from app.schemas.user import (
    AdminRegisterRequest,
    FacultyRegisterRequest,
    StudentProfileUpdateRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.api.deps import get_current_user

router = APIRouter()


def _normalize_role(role) -> UserRole:
    """Normalize a role value returned by SQLAlchemy."""
    if isinstance(role, UserRole):
        return role

    return UserRole(str(role).upper())


def _get_authorized_enrollment(
    db: Session,
    enrollment_number: str,
    expected_role: UserRole,
    expected_admin_job_role: str | None = None,
) -> AuthorizedEnrollment:
    """Validate that an enrollment number is authorized for the requested role."""
    authorization = (
        db.query(AuthorizedEnrollment)
        .filter(
            AuthorizedEnrollment.enrollment_number == enrollment_number,
            AuthorizedEnrollment.is_active.is_(True),
        )
        .with_for_update()
        .first()
    )

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This enrollment number is not authorized for registration.",
        )

    if _normalize_role(authorization.expected_role) != expected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This enrollment number is not authorized for this account type.",
        )

    if expected_role == UserRole.ADMIN:
        authorized_job_role = (authorization.admin_job_role or "").strip().upper()
        requested_job_role = (expected_admin_job_role or "").strip().upper()
        if not authorized_job_role or authorized_job_role != requested_job_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This enrollment number is not authorized for the requested administrative job role. Contact a SUPER_ADMIN for provisioning.",
            )

    if authorization.claimed_by_user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This enrollment number has already been registered.",
        )

    return authorization


def _check_duplicate_account(
    db: Session,
    email: str,
    enrollment_number: str,
) -> None:
    """Reject duplicate emails and enrollment numbers."""
    if db.query(User.id).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    if (
        db.query(User.id)
        .filter(User.enrollment_number == enrollment_number)
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This enrollment number is already associated with an account.",
        )


def _create_account(
    db: Session,
    *,
    name: str,
    email: str,
    enrollment_number: str,
    password: str,
    role: UserRole,
    authorization: AuthorizedEnrollment,
    academic_course: str | None = None,
    admin_job_role: str | None = None,
    year_of_study: str | None = None,
    semester: str | None = None,
    approval_status: str = "APPROVED",
) -> User:
    """Create an account and claim its authorized enrollment number."""
    user = User(
        name=name.strip(),
        email=email.strip().lower(),
        enrollment_number=enrollment_number,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        academic_course=academic_course,
        admin_job_role=admin_job_role,
        year_of_study=year_of_study,
        semester=semester,
        approval_status=approval_status,
    )

    db.add(user)
    db.flush()

    authorization.claimed_by_user_id = user.id

    db.commit()
    db.refresh(user)

    return user


def _create_pending_approval_record(
    db: Session,
    user: User,
    account_type: str,
) -> RegistrationApproval:
    """Create the audit/approval record for a pending faculty or admin registration."""
    record = RegistrationApproval(
        applicant_id=user.id,
        account_type=account_type,
        decision="PENDING",
    )
    db.add(record)
    db.commit()
    return record


def _issue_token(user: User) -> TokenResponse:
    """Issue a JWT using the role stored in the database."""
    role = _normalize_role(user.role)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": role.value,
            "email": user.email,
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a student account",
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a student using an authorized MUR enrollment number."""
    authorization = None

    try:
        _check_duplicate_account(
            db,
            payload.email,
            payload.enrollment_number,
        )

        authorization = _get_authorized_enrollment(
            db,
            payload.enrollment_number,
            UserRole.STUDENT,
        )

        if authorization.course_id is not None:
            course = (
                db.query(Course)
                .filter(
                    Course.id == authorization.course_id,
                    Course.is_active.is_(True),
                )
                .first()
            )

            if course is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The course associated with this enrollment is unavailable.",
                )

        user = _create_account(
            db,
            name=payload.name,
            email=str(payload.email),
            enrollment_number=payload.enrollment_number,
            password=payload.password,
            role=UserRole.STUDENT,
            authorization=authorization,
            academic_course=payload.academic_course,
            year_of_study=payload.year_of_study,
            semester=payload.semester,
        )

        return UserResponse.model_validate(user)

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The account could not be registered because a unique value already exists.",
        ) from None
    except Exception:
        db.rollback()
        raise


@router.post(
    "/register/faculty",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a faculty account",
)
def register_faculty(
    payload: FacultyRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Register faculty using an authorized EMP enrollment number.

    Selected teaching subjects are preferences only. They do not grant
    course-management permissions.
    """
    try:
        _check_duplicate_account(
            db,
            payload.email,
            payload.enrollment_number,
        )

        authorization = _get_authorized_enrollment(
            db,
            payload.enrollment_number,
            UserRole.FACULTY,
        )

        user = _create_account(
            db,
            name=payload.name,
            email=str(payload.email),
            enrollment_number=payload.enrollment_number,
            password=payload.password,
            role=UserRole.FACULTY,
            authorization=authorization,
            approval_status="PENDING",
        )

        # Create pending approval audit record
        _create_pending_approval_record(db, user, "FACULTY")

        # Teaching-subject persistence requires a dedicated relationship
        # model. Do not create course assignments from signup preferences.

        # Return 202-style response with pending message embedded in the user object.
        # The account exists but has no dashboard access until approved.
        return UserResponse.model_validate(user)

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The account could not be registered because a unique value already exists.",
        ) from None
    except Exception:
        db.rollback()
        raise


@router.post(
    "/register/admin",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an authorized administrator",
)
def register_admin(
    payload: AdminRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Register an administrator only if their enrollment number is explicitly
    authorized as ADMIN in the database.

    An EMP prefix alone never grants administrative privileges.
    """
    try:
        if payload.admin_job_role == "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SUPER_ADMIN accounts cannot be created through public registration.",
            )

        _check_duplicate_account(
            db,
            payload.email,
            payload.enrollment_number,
        )

        authorization = _get_authorized_enrollment(
            db,
            payload.enrollment_number,
            UserRole.ADMIN,
            expected_admin_job_role=payload.admin_job_role,
        )

        user = _create_account(
            db,
            name=payload.name,
            email=str(payload.email),
            enrollment_number=payload.enrollment_number,
            password=payload.password,
            role=UserRole.ADMIN,
            authorization=authorization,
            admin_job_role=payload.admin_job_role,
            approval_status="PENDING",
        )

        # Create pending approval audit record (requires SUPER_ADMIN to approve)
        _create_pending_approval_record(db, user, "ADMIN")

        return UserResponse.model_validate(user)

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The account could not be registered because a unique value already exists.",
        ) from None
    except Exception:
        db.rollback()
        raise


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with enrollment number and password",
)
def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate an existing account.

    Login never creates accounts or changes roles. The account's role is
    obtained from the database, not from the enrollment-number prefix.
    """
    user = (
        db.query(User)
        .filter(User.enrollment_number == payload.enrollment_number)
        .first()
    )

    if user is None or not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid enrollment number or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Please contact an administrator.",
        )

    # Block accounts that are still awaiting approval
    approval = getattr(user, "approval_status", "APPROVED")
    if approval == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your account is pending approval. "
                "An administrator will review your registration and notify you."
            ),
        )
    if approval == "REJECTED":
        rejection_record = (
            db.query(RegistrationApproval)
            .filter(RegistrationApproval.applicant_id == user.id)
            .order_by(RegistrationApproval.reviewed_at.desc())
            .first()
        )
        reason = (
            rejection_record.rejection_reason
            if rejection_record and rejection_record.rejection_reason
            else "No reason provided."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your registration was not approved. Reason: {reason}",
        )

    return _issue_token(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user's profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's safe profile."""
    return UserResponse.model_validate(current_user)


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update a student's academic profile",
)
@router.patch(
    "/profile",
    response_model=UserResponse,
    summary="Update a student's academic profile",
)
def update_student_profile(
    payload: StudentProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Update the student's academic profile and run the existing course
    auto-enrollment service.
    """
    if _normalize_role(current_user.role) != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Academic profiling is restricted to student accounts.",
        )

    clean_student_id = payload.student_id_number.strip()

    duplicate = (
        db.query(User)
        .filter(
            User.student_id_number == clean_student_id,
            User.id != current_user.id,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student ID is already registered to another student.",
        )

    try:
        current_user.student_id_number = clean_student_id
        current_user.academic_course = payload.academic_course.strip()
        current_user.academic_year = payload.academic_year.strip()
        current_user.semester = payload.semester.strip()
        current_user.year_of_study = payload.year_of_study.strip()

        db.commit()
        db.refresh(current_user)

        from app.services.enrollment import (
            auto_enroll_student_in_matching_courses,
        )

        auto_enroll_student_in_matching_courses(current_user, db)

        db.refresh(current_user)

        return UserResponse.model_validate(current_user)

    except Exception:
        db.rollback()
        raise