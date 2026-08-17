from types import SimpleNamespace
from aios.services.review_service import ReviewService

class Repo:
    def __init__(self):
        self.rows = [
            SimpleNamespace(id='r1', review_type='possible_duplicate', state='pending', payload={'requested_action':'create_anyway'}),
            SimpleNamespace(id='r2', review_type='possible_duplicate', state='pending', payload={}),
        ]
    def get_open_reviews(self): return list(self.rows)

# Avoid exercising identity conversion for the visible row; this smoke is only
# proving the already-decided row is filtered before conversion.
service = ReviewService.__new__(ReviewService)
service.review_repository = Repo()
service._to_app_review = lambda r: r
rows = service.list_pending_reviews()
assert [r.id for r in rows] == ['r2']
print('Durably decided create_anyway review hidden immediately: PASS')
print('Undecided duplicate review remains visible: PASS')
print('RESULT: POSSIBLE DUPLICATE REVIEW RESPONSIVENESS V1 SMOKE TEST PASSED')
