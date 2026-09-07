"""Centralized arXiv category → human-readable topic mapping.

Raw taxonomy codes belong in ``source_categories``. Mapped labels belong in
``topics``. Unknown codes are preserved as source categories only and never
fabricated into display topics.
"""

from __future__ import annotations

import logging
import re

from app.services.query_normalization import normalize_topic_list

logger = logging.getLogger(__name__)

# Broad parent domains appear before more specific mapped topics.
_DOMAIN_ORDER = (
    "Computer Science",
    "Statistics",
    "Electrical Engineering and Systems Science",
    "Mathematics",
    "Physics",
    "Quantitative Biology",
    "Quantitative Finance",
    "Economics",
)

# Expandable map: one category → one or more canonical display topics.
# Keep labels stable and title-cased for user-facing chips.
ARXIV_CATEGORY_TOPICS: dict[str, list[str]] = {
    # Computer Science
    "cs.AI": ["Computer Science", "Artificial Intelligence"],
    "cs.AR": ["Computer Science", "Hardware Architecture"],
    "cs.CC": ["Computer Science", "Computational Complexity"],
    "cs.CE": ["Computer Science", "Computational Engineering"],
    "cs.CG": ["Computer Science", "Computational Geometry"],
    "cs.CL": ["Computer Science", "Natural Language Processing"],
    "cs.CR": ["Computer Science", "Cryptography and Security"],
    "cs.CV": ["Computer Science", "Computer Vision"],
    "cs.CY": ["Computer Science", "Computers and Society"],
    "cs.DB": ["Computer Science", "Databases"],
    "cs.DC": ["Computer Science", "Distributed Computing"],
    "cs.DL": ["Computer Science", "Digital Libraries"],
    "cs.DM": ["Computer Science", "Discrete Mathematics"],
    "cs.DS": ["Computer Science", "Data Structures and Algorithms"],
    "cs.ET": ["Computer Science", "Emerging Technologies"],
    "cs.FL": ["Computer Science", "Formal Languages"],
    "cs.GL": ["Computer Science", "General Literature"],
    "cs.GR": ["Computer Science", "Graphics"],
    "cs.GT": ["Computer Science", "Computer Science and Game Theory"],
    "cs.HC": ["Computer Science", "Human-Computer Interaction"],
    "cs.IR": ["Computer Science", "Information Retrieval"],
    "cs.IT": ["Computer Science", "Information Theory"],
    "cs.LG": ["Computer Science", "Machine Learning"],
    "cs.LO": ["Computer Science", "Logic in Computer Science"],
    "cs.MA": ["Computer Science", "Multiagent Systems"],
    "cs.MM": ["Computer Science", "Multimedia"],
    "cs.MS": ["Computer Science", "Mathematical Software"],
    "cs.NA": ["Computer Science", "Numerical Analysis"],
    "cs.NE": ["Computer Science", "Neural and Evolutionary Computing"],
    "cs.NI": ["Computer Science", "Networking and Internet Architecture"],
    "cs.OH": ["Computer Science", "Other Computer Science"],
    "cs.OS": ["Computer Science", "Operating Systems"],
    "cs.PF": ["Computer Science", "Performance"],
    "cs.PL": ["Computer Science", "Programming Languages"],
    "cs.RO": ["Computer Science", "Robotics"],
    "cs.SC": ["Computer Science", "Symbolic Computation"],
    "cs.SD": ["Computer Science", "Sound"],
    "cs.SE": ["Computer Science", "Software Engineering"],
    "cs.SI": ["Computer Science", "Social and Information Networks"],
    "cs.SY": ["Computer Science", "Systems and Control"],
    # Statistics
    "stat.AP": ["Statistics", "Applications"],
    "stat.CO": ["Statistics", "Computation"],
    "stat.ME": ["Statistics", "Methodology"],
    "stat.ML": ["Statistics", "Machine Learning"],
    "stat.OT": ["Statistics", "Other Statistics"],
    "stat.TH": ["Statistics", "Statistics Theory"],
    # Electrical Engineering and Systems Science
    "eess.AS": [
        "Electrical Engineering and Systems Science",
        "Audio and Speech Processing",
    ],
    "eess.IV": [
        "Electrical Engineering and Systems Science",
        "Image and Video Processing",
    ],
    "eess.SP": [
        "Electrical Engineering and Systems Science",
        "Signal Processing",
    ],
    "eess.SY": [
        "Electrical Engineering and Systems Science",
        "Systems and Control",
    ],
    # Quantitative Biology (common ML-adjacent)
    "q-bio.BM": ["Quantitative Biology", "Biomolecules"],
    "q-bio.CB": ["Quantitative Biology", "Cell Behavior"],
    "q-bio.GN": ["Quantitative Biology", "Genomics"],
    "q-bio.MN": ["Quantitative Biology", "Molecular Networks"],
    "q-bio.NC": ["Quantitative Biology", "Neurons and Cognition"],
    "q-bio.OT": ["Quantitative Biology", "Other Quantitative Biology"],
    "q-bio.PE": ["Quantitative Biology", "Populations and Evolution"],
    "q-bio.QM": ["Quantitative Biology", "Quantitative Methods"],
    "q-bio.SC": ["Quantitative Biology", "Subcellular Processes"],
    "q-bio.TO": ["Quantitative Biology", "Tissues and Organs"],
    # Math (common overlaps)
    "math.ST": ["Mathematics", "Statistics Theory"],
    "math.OC": ["Mathematics", "Optimization and Control"],
    "math.PR": ["Mathematics", "Probability"],
    "math.NA": ["Mathematics", "Numerical Analysis"],
}

# arXiv category codes look like "cs.CV", "stat.ML", "q-bio.NC", "math.OC".
# Keep this permissive enough that unknown-but-code-shaped values stay in
# source_categories instead of leaking into display topics.
_ARXIV_CATEGORY_RE = re.compile(
    r"^[a-z]{2,5}(?:-[a-z]+)?\.[A-Za-z][A-Za-z0-9_-]*$"
)


def is_arxiv_category_code(value: str) -> bool:
    """Return True when ``value`` looks like an arXiv taxonomy code."""
    text = (value or "").strip()
    if not text:
        return False
    return _ARXIV_CATEGORY_RE.fullmatch(text) is not None


def normalize_arxiv_category(value: str) -> str:
    """Normalize category casing: archive lower, subject class upper-ish.

    Examples:
        ``CS.cv`` → ``cs.CV``
        ``stat.ml`` → ``stat.ML``
    """
    text = (value or "").strip()
    if "." not in text:
        return text.casefold()
    archive, _, subject = text.partition(".")
    return f"{archive.casefold()}.{subject.upper()}"


def map_arxiv_categories_to_topics(
    categories: list[str] | None,
    *,
    log_unknown: bool = False,
) -> list[str]:
    """Map raw arXiv categories to deduped, deterministically ordered topics.

    Unknown categories do not crash and do not become display topics.
    """
    if not categories:
        return []

    seen_domains: set[str] = set()
    seen_specifics: set[str] = set()
    specific_topics: list[str] = []
    unknown: list[str] = []

    for raw in categories:
        if not raw or not isinstance(raw, str):
            continue
        code = normalize_arxiv_category(raw)
        mapped = ARXIV_CATEGORY_TOPICS.get(code)
        if not mapped:
            mapped = ARXIV_CATEGORY_TOPICS.get(raw.strip())
        if not mapped:
            unknown.append(code or raw.strip())
            continue

        for topic in mapped:
            key = topic.casefold()
            if topic in _DOMAIN_ORDER:
                seen_domains.add(topic)
                continue
            if key in seen_specifics:
                continue
            seen_specifics.add(key)
            specific_topics.append(topic)

    if log_unknown and unknown:
        logger.debug("Unmapped arXiv categories: %s", sorted(set(unknown)))

    ordered_domains = [d for d in _DOMAIN_ORDER if d in seen_domains]
    return normalize_topic_list([*ordered_domains, *specific_topics])
