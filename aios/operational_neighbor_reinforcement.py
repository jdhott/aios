import re


GENERIC_OPERATIONAL_WORDS = {
    "management",
    "operations",
    "maintenance",
    "organization",
    "coordination",
    "supplies",
    "equipment",
    "workflow",
    "cleanup",
    "preparation",
}


def normalize_tokens(text):

    tokens = re.findall(
        r"[a-zA-Z]+",
        str(text or "").lower(),
    )

    return [
        token
        for token in tokens
        if len(token) > 2
    ]


def operational_overlap_score(
    candidate_title,
    neighbor_title,
):

    candidate_tokens = set(
        normalize_tokens(candidate_title)
    )

    neighbor_tokens = set(
        normalize_tokens(neighbor_title)
    )

    if not candidate_tokens or not neighbor_tokens:
        return 0.0

    overlap = (
        candidate_tokens
        & neighbor_tokens
    )

    meaningful_overlap = [

        token
        for token in overlap
        if token not in GENERIC_OPERATIONAL_WORDS
    ]

    score = (
        len(meaningful_overlap)
        / max(
            len(candidate_tokens),
            len(neighbor_tokens),
        )
    )

    return round(score, 2)


def build_operational_neighbors(tasks):

    operational_memory = {}

    for task in tasks:

        title = (
            task.get("title")
            or task.get("Task Name")
            or ""
        )

        project = (
            task.get("project")
            or task.get("Project")
            or ""
        )

        if not title or not project:
            continue

        operational_memory.setdefault(
            project,
            []
        ).append(title)

    return operational_memory


def infer_operational_domain(
    candidate_title,
    operational_memory,
):

    scored_projects = []

    for project_name, neighbors in (
        operational_memory.items()
    ):

        scores = []

        for neighbor in neighbors:

            overlap = operational_overlap_score(
                candidate_title,
                neighbor,
            )

            if overlap > 0:
                scores.append(overlap)

        if not scores:
            continue

        reinforcement = (
            sum(scores)
            / len(scores)
        )

        reinforcement += (
            min(len(neighbors), 10)
            * 0.03
        )

        scored_projects.append(
            (
                round(reinforcement, 2),
                project_name,
            )
        )

    scored_projects.sort(
        reverse=True,
    )

    if not scored_projects:

        return {
            "project": None,
            "score": 0.0,
            "reason":
                "No operational neighbors found.",
        }

    best_score, best_project = (
        scored_projects[0]
    )

    return {

        "project": best_project,
        "score": best_score,
        "reason":
            "Operational neighbor reinforcement "
            "selected dominant execution domain.",
    }