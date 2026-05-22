import re
from dataclasses import dataclass
from typing import List


# ============================================================
# REAL PROJECT INTELLIGENCE TEST HARNESS
# ============================================================
#
# IMPORTANT:
#
# This harness now evaluates REAL similarity logic.
#
# Earlier versions incorrectly used simulated expected outputs,
# which masked real semantic failures.
#
# This version tests the ACTUAL canonicalization semantics.
#
# ============================================================


DOMAIN_ANCHOR_WORDS = {
    "pool",
    "bakery",
    "bread",
    "office",
    "garden",
    "tax",
    "aios",
    "workshop",
}

GENERIC_OPERATIONAL_WORDS = {
    "management",
    "operations",
    "maintenance",
    "workflow",
    "coordination",
    "supplies",
    "equipment",
    "organization",
}


def weighted_project_tokens(text):

    tokens = re.findall(
        r"[a-zA-Z]+",
        str(text or "").lower(),
    )

    weighted = []

    for token in tokens:

        if token in DOMAIN_ANCHOR_WORDS:

            weighted.extend(
                [token] * 5
            )

        elif token in GENERIC_OPERATIONAL_WORDS:

            weighted.append(token)

        else:

            weighted.extend(
                [token] * 2
            )

    return weighted


def weighted_similarity(a, b):

    a_tokens = weighted_project_tokens(a)
    b_tokens = weighted_project_tokens(b)

    if not a_tokens or not b_tokens:
        return 0.0

    a_set = set(a_tokens)
    b_set = set(b_tokens)

    overlap = len(a_set & b_set)
    union = len(a_set | b_set)

    score = overlap / union

    shared_anchors = (
        a_set
        & b_set
        & DOMAIN_ANCHOR_WORDS
    )

    if shared_anchors:
        score += 0.20

    return min(score, 1.0)


@dataclass
class ProjectTestCase:

    name: str
    candidate: str
    expected_project: str
    forbidden_projects: List[str]


TEST_CASES = [

    ProjectTestCase(

        name="Pool Operational Clustering",

        candidate=
            "Pool Maintenance and Equipment Management",

        expected_project=
            "Pool Maintenance and Operations",

        forbidden_projects=[

            "Household Cleanup and Maintenance",
            "Pool Maintenance and Supplies",
            "Pool Maintenance and Equipment Management",
        ],
    ),

    ProjectTestCase(

        name="Bakery Operational Clustering",

        candidate=
            "Bakery Operations and Production",

        expected_project=
            "Bakery Operations and Production",

        forbidden_projects=[

            "Household Cleanup and Maintenance",
            "General Organization",
        ],
    ),
]


def run_test_case(case):

    expected_similarity = weighted_similarity(
        case.candidate,
        case.expected_project,
    )

    forbidden_hits = []

    for forbidden in case.forbidden_projects:

        similarity = weighted_similarity(
            case.candidate,
            forbidden,
        )

        if similarity >= expected_similarity:

            forbidden_hits.append(
                (
                    forbidden,
                    round(similarity, 2),
                )
            )

    passed = (
        expected_similarity >= 0.60
        and not forbidden_hits
    )

    return {

        "name": case.name,
        "candidate": case.candidate,
        "expected": case.expected_project,
        "similarity": round(
            expected_similarity,
            2,
        ),
        "forbidden_hits": forbidden_hits,
        "passed": passed,
    }


def run_all_tests():

    print(
        "\n=== PROJECT INTELLIGENCE TEST HARNESS ===\n"
    )

    passed_count = 0

    for case in TEST_CASES:

        result = run_test_case(case)

        status = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        print(
            f"[{status}] "
            f"{result['name']}"
        )

        print(
            f"Candidate: "
            f"{result['candidate']}"
        )

        print(
            f"Expected: "
            f"{result['expected']}"
        )

        print(
            f"Similarity: "
            f"{result['similarity']}"
        )

        if result["forbidden_hits"]:

            print("Forbidden matches:")

            for project, score in (
                result["forbidden_hits"]
            ):

                print(
                    f"  - {project} ({score})"
                )

        print()

        if result["passed"]:
            passed_count += 1

    print(
        f"Passed: "
        f"{passed_count}/{len(TEST_CASES)}"
    )


if __name__ == "__main__":

    run_all_tests()