import uuid
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def api_post(path, data, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    res = client.post(path, json=data, headers=headers)
    assert res.status_code in (200, 201), f"POST {path} failed: {res.text}"
    return res.json()

def api_put(path, data, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    res = client.put(path, json=data, headers=headers)
    return res

def api_get(path, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    res = client.get(path, headers=headers)
    assert res.status_code == 200, f"GET {path} failed: {res.text}"
    return res.json()

print("--- Testing Password Suffix Role Detection ---")
res_fac = api_post('/api/auth/login', {'email': 'prof@university.edu', 'password': 'teacher123-fac'})
print(f"Prof login: role={res_fac['user']['role']} (Expected: FACULTY)")
assert res_fac['user']['role'] == 'FACULTY'

res_ad = api_post('/api/auth/login', {'email': 'root@university.edu', 'password': 'secure123-ad'})
print(f"Root login: role={res_ad['user']['role']} (Expected: ADMIN)")
assert res_ad['user']['role'] == 'ADMIN'

res_stu = api_post('/api/auth/login', {'email': 'alice@student.edu', 'password': 'mypassword'})
print(f"Alice login: role={res_stu['user']['role']}, profile_completed={res_stu['user']['profile_completed']} (Expected: STUDENT, False)")
assert res_stu['user']['role'] == 'STUDENT'
assert res_stu['user']['profile_completed'] is False
student_token = res_stu['access_token']

print("\n--- Testing Academic Profile Completion ---")
prof_data = {
    'student_id_number': f'STU-{uuid.uuid4().hex[:6].upper()}',
    'academic_course': 'Computer Science & Engineering',
    'academic_year': '2026-2027',
    'semester': 'Fall 2026'
}
res_update = api_put('/api/auth/profile', prof_data, token=student_token)
assert res_update.status_code == 200
updated_stu = res_update.json()
print(f"Updated profile: student_id={updated_stu['student_id_number']}, profile_completed={updated_stu['profile_completed']} (Expected: {prof_data['student_id_number']}, True)")
assert updated_stu['student_id_number'] == prof_data['student_id_number']
assert updated_stu['profile_completed'] is True

print("\n--- Testing Duplicate Student ID Rejection ---")
res_bob = api_post('/api/auth/login', {'email': 'bob@student.edu', 'password': 'bobpassword'})
bob_token = res_bob['access_token']
bob_update = api_put('/api/auth/profile', prof_data, token=bob_token)
print(f"Duplicate student ID rejected with HTTP {bob_update.status_code} (Expected: 409)")
assert bob_update.status_code == 409

print("\n--- Testing Course Creation & Auto-Enrollment ---")
faculty_token = res_fac['access_token']
course_code = f"CS{uuid.uuid4().hex[:4].upper()}"
course_payload = {
    'code': course_code,
    'name': 'Data Structures Lab',
    'description': 'Core practicals',
    'semester': 'Fall 2026',
    'academic_year': '2026-2027',
    'is_active': True
}
course_res = api_post('/api/courses', course_payload, token=faculty_token)
print(f"Faculty created course: {course_res['code']} ({course_res['name']})")

alice_courses = api_get('/api/courses', token=student_token)
enrolled_codes = [c['code'] for c in alice_courses]
print(f"Alice's visible courses: {enrolled_codes}")
assert course_code in enrolled_codes, f"{course_code} not in {enrolled_codes}"
print(f"SUCCESS: Course {course_code} automatically matched and visible to Alice!")

print("\nALL BACKEND VERIFICATION TESTS PASSED SUCCESSFULLY!")
