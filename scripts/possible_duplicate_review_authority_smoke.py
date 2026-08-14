#!/usr/bin/env python3
from datetime import datetime, timezone
from aios.review.models import InboxReview
from aios.review.possible_duplicate_transitions import resolve_possible_duplicate_review
class Repo:
    def resolve_review(self, review_id, *, decision):
        return InboxReview(id=review_id,inbox_item_id='i',review_type='possible_duplicate',state='resolved',decision=decision,resolved_at=datetime.now(timezone.utc))
def pending(): return InboxReview(id='r',inbox_item_id='i',review_type='possible_duplicate',state='pending',payload={})
for action in ('link_existing','ignore'):
    r=resolve_possible_duplicate_review(review_repo=Repo(),review=pending(),action=action,candidate_task_id='existing',candidate_task_title='Existing')
    assert r.state=='resolved' and r.decision['action']==action
r=resolve_possible_duplicate_review(review_repo=Repo(),review=pending(),action='create_anyway',candidate_task_id='existing',created_task_ids=['new'])
assert r.decision['created_task_ids']==['new']
try: resolve_possible_duplicate_review(review_repo=Repo(),review=pending(),action='bad')
except ValueError: pass
else: raise RuntimeError('bad action accepted')
print('link_existing transition: PASS')
print('ignore transition: PASS')
print('create_anyway transition: PASS')
print('unsupported action rejection: PASS')
print('RESULT: POSSIBLE DUPLICATE REVIEW AUTHORITY CUTOVER SMOKE TEST PASSED')
