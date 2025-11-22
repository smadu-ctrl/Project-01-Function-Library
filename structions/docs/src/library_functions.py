"""
reddit_analytics.py

Object-oriented refactor of Project 1 functions into classes for Project 2.

Classes:
- RedditPost          : encapsulates a single post and its basic methods
- PostValidator       : static/instance validators for posts and dates
- PostCategorizer     : keyword-based categorization (integrates clean_text)
- TrendAnalyzer       : aggregate/weekly analysis utilities (top posts, filtering)
- SemesterReporter    : reporting & export helpers (CSV generation / summary)


"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import re
import csv
import statistics
import json


class PostValidator:
    """Validation utilities for post dictionaries and dates.

    Methods:
        validate_post_data(post) -> bool
        is_valid_date(date_str) -> bool

    Example:
        PostValidator.is_valid_date("2025-10-01")  # True
    """

    DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    @staticmethod
    def is_valid_date(date_str: str) -> bool:
        """Validate 'YYYY-MM-DD' format and that it is a real date."""
        if not isinstance(date_str, str):
            return False
        if not PostValidator.DATE_RE.match(date_str):
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_post_data(post: dict) -> bool:
        """Check required fields and types for a Reddit post dict.

        Required keys: title(str), score(int), num_comments(int), created_utc(int)

        Raises:
            ValueError if any required field is missing or wrong type.
        """
        if not isinstance(post, dict):
            raise ValueError("Post must be a dict")

        required = {
            "title": str,
            "score": int,
            "num_comments": int,
            "created_utc": int,  # seconds since epoch
        }
        for key, t in required.items():
            if key not in post:
                raise ValueError(f"Missing required field: {key}")
            if not isinstance(post[key], t):
                # allow ints that are subclasses (e.g., bool is subclass of int) -> disallow bool
                if t is int and isinstance(post[key], bool):
                    raise ValueError(f"Field {key} must be int, not bool")
                if not isinstance(post[key], t):
                    raise ValueError(f"Field {key} must be {t.__name__}")
        return True


class RedditPost:
    """Represents a Reddit post and provides basic transformations.

    Attributes (private):
        _title, _body, _score, _num_comments, _created_utc

    Methods:
        engagement_score() -> int
        format_datetime() -> str
        clean_text() -> str
        to_dict() -> dict

    Example:
        p = RedditPost("Hi", "Body", 10, 2, 1690000000)
        p.engagement_score()  # 30 (by default: upvotes + 2*comments)
    """

    def __init__(self, title: str, body: str, score: int, num_comments: int, created_utc: int):
        # validation (defensive)
        if not title or not isinstance(title, str):
            raise ValueError("title must be a non-empty string")
        if body is None:
            body = ""
        if not isinstance(score, int) or isinstance(score, bool):
            raise ValueError("score must be an int")
        if not isinstance(num_comments, int) or isinstance(num_comments, bool):
            raise ValueError("num_comments must be an int")
        if not isinstance(created_utc, int) or created_utc < 0:
            raise ValueError("created_utc must be a non-negative int (seconds)")
        self._title = title
        self._body = body
        self._score = score
        self._num_comments = num_comments
        self._created_utc = created_utc
        # cache cleaned text
        self._cleaned_text: Optional[str] = None

    # Properties (read-only for core fields)
    @property
    def title(self) -> str:
        return self._title

    @property
    def body(self) -> str:
        return self._body

    @property
    def score(self) -> int:
        return self._score

    @property
    def num_comments(self) -> int:
        return self._num_comments

    @property
    def created_utc(self) -> int:
        return self._created_utc

    def engagement_score(self, w_upvote: float = 1.0, w_comment: float = 2.0) -> int:
        """Combine upvotes and comments into single metric.

        Default: engagement = upvotes * 1 + comments * 2

        Args:
            w_upvote: weight for upvotes
            w_comment: weight for comments

        Returns:
            int (rounded)
        """
        score = self._score * w_upvote + self._num_comments * w_comment
        return int(round(score))

    def format_datetime(self, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Convert stored timestamp (seconds) into human readable string."""
        dt = datetime.utcfromtimestamp(self._created_utc)
        return dt.strftime(fmt)

    def clean_text(self) -> str:
        """Return cached cleaned text of title+body.

        Cleaning steps:
          - lowercasing
          - remove punctuation (simple)
          - remove emojis and non-alphanumeric (keeps spaces)
        """
        if self._cleaned_text is not None:
            return self._cleaned_text
        combined = f"{self._title} {self._body}".lower()
        # Remove emojis / non-alphanumeric except spaces
        combined = re.sub(r"[^\w\s]", " ", combined, flags=re.UNICODE)
        # collapse spaces
        combined = re.sub(r"\s+", " ", combined).strip()
        self._cleaned_text = combined
        return combined

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict representation."""
        return {
            "title": self._title,
            "body": self._body,
            "score": self._score,
            "num_comments": self._num_comments,
            "created_utc": self._created_utc,
            "engagement": self.engagement_score(),
        }

    def __str__(self):
        return f"RedditPost(title={self._title!r}, score={self._score}, comments={self._num_comments})"

    def __repr__(self):
        return f"RedditPost({self._title!r}, score={self._score}, comments={self._num_comments})"


class PostCategorizer:
    """Categorize posts into predefined categories using keyword matching.

    - Encapsulates category keyword sets
    - Uses RedditPost.clean_text() for matching

    Methods:
        categorize(post) -> str
        add_category(name, keywords) -> None
        category_counts(posts) -> Dict[str,int]

    Example:
        cat = PostCategorizer()
        cat.categorize(post_instance)
    """

    def __init__(self, categories: Optional[Dict[str, List[str]]] = None):
        # default six categories and keywords (example)
        default = {
            "question": ["how", "what", "why", "help", "question"],
            "news": ["breaking", "announcement", "news"],
            "discussion": ["discussion", "debate", "opinion"],
            "meme": ["meme", "funny", "lol"],
            "advice": ["advice", "recommend", "should i"],
            "other": [],
        }
        self._categories: Dict[str, List[str]] = categories if categories is not None else default

    @property
    def categories(self) -> Dict[str, List[str]]:
        """Return a shallow copy of categories to prevent mutation."""
        return dict(self._categories)

    def add_category(self, name: str, keywords: List[str]):
        """Add or replace a category's keyword list."""
        if not name or not isinstance(name, str):
            raise ValueError("Category name must be a non-empty string")
        if not isinstance(keywords, list):
            raise ValueError("Keywords must be a list of strings")
        self._categories[name] = [k.lower() for k in keywords]

    def categorize(self, post: RedditPost) -> str:
        """Return the best category match for a RedditPost.

        Strategy: check presence of keywords (word boundaries) in cleaned text.
        If multiple categories match, return the one with the most keyword hits.
        If none match, return 'other'.
        """
        cleaned = post.clean_text()
        hits: Dict[str, int] = {}
        for cat, kws in self._categories.items():
            if not kws:
                hits[cat] = 0
                continue
            count = 0
            for kw in kws:
                # simple word boundary check
                pattern = r"\b" + re.escape(kw.lower()) + r"\b"
                if re.search(pattern, cleaned):
                    count += 1
            hits[cat] = count
        # pick best (ties: highest count; if tie and >0 chooses first by insertion order)
        best_cat = max(hits.items(), key=lambda kv: kv[1])[0]
        if hits[best_cat] == 0:
            return "other"
        return best_cat

    def category_counts(self, posts: List[RedditPost]) -> Dict[str, int]:
        """Return counts per category for a list of posts."""
        counts = {k: 0 for k in self._categories.keys()}
        counts.setdefault("other", 0)
        for p in posts:
            cat = self.categorize(p)
            counts.setdefault(cat, 0)
            counts[cat] += 1
        return counts


class TrendAnalyzer:
    """Aggregation and analysis utilities.

    Methods:
        get_top_posts(posts, n) -> List[RedditPost]
        filter_posts_by_date(posts, start, end) -> List[RedditPost]
        aggregate_semester_data(posts) -> Dict[str, Dict[str,float]]
        compare_trends_over_time(weekly_counts) -> Dict[str, Dict[str,float]]
    """

    def __init__(self, categorizer: Optional[PostCategorizer] = None):
        self._categorizer = categorizer if categorizer is not None else PostCategorizer()

    def get_top_posts(self, posts: List[RedditPost], n: int = 10) -> List[RedditPost]:
        """Return top n posts sorted by engagement_score (desc)."""
        return sorted(posts, key=lambda p: p.engagement_score(), reverse=True)[:n]

    def filter_posts_by_date(self, posts: List[RedditPost], start: str, end: str) -> List[RedditPost]:
        """Return posts whose created_utc falls between start and end inclusive.

        start and end: 'YYYY-MM-DD' format. Uses UTC midnight bounds.
        """
        if not (PostValidator.is_valid_date(start) and PostValidator.is_valid_date(end)):
            raise ValueError("start and end must be YYYY-MM-DD")
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        return [p for p in posts if start_ts <= p.created_utc <= end_ts]

    def aggregate_semester_data(self, all_posts: List[RedditPost]) -> Dict[str, Dict[str, float]]:
        """Calculate count and average engagement per category for given posts."""
        categories = self._categorizer.categories.keys()
        agg: Dict[str, Dict[str, float]] = {c: {"count": 0, "avg_engagement": 0.0} for c in categories}
        agg.setdefault("other", {"count": 0, "avg_engagement": 0.0})
        groups: Dict[str, List[int]] = {c: [] for c in agg.keys()}

        for p in all_posts:
            cat = self._categorizer.categorize(p)
            groups.setdefault(cat, [])
            groups[cat].append(p.engagement_score())

        for cat, scores in groups.items():
            if not scores:
                agg[cat] = {"count": 0, "avg_engagement": 0.0}
            else:
                agg[cat] = {"count": len(scores), "avg_engagement": statistics.mean(scores)}
        return agg

    def compare_trends_over_time(self, weekly_data: List[Dict[str, int]]) -> Dict[str, Dict[str, float]]:
        """Compute percentage change week-over-week for each category.

        weekly_data: list of dicts, each dict = {category: count} in chronological order.
        Returns: {category: {"pct_changes": [..], "latest": x}} with pct changes for each step.
        """
        if not weekly_data:
            return {}
        # collect categories set
        cats = set()
        for wk in weekly_data:
            cats.update(wk.keys())
        result: Dict[str, Dict[str, float]] = {}
        for cat in cats:
            vals = [wk.get(cat, 0) for wk in weekly_data]
            pct_changes = []
            for i in range(1, len(vals)):
                prev = vals[i - 1]
                curr = vals[i]
                if prev == 0:
                    pct = float("inf") if curr != 0 else 0.0
                else:
                    pct = ((curr - prev) / prev) * 100.0
                pct_changes.append(pct)
            result[cat] = {"pct_changes": pct_changes, "latest": vals[-1]}
        return result


class SemesterReporter:
    """Generate CSV, JSON, and human-readable summaries for semester analysis.

    Methods:
        generate_summary_csv(analysis_results, path)
        generate_summary_json(analysis_results, path)
        summarize_semester_findings(semester_summary, trend_changes) -> str
    """

    def __init__(self, author: str = "Analyst"):
        if not author:
            raise ValueError("author must be non-empty")
        self._author = author

    @property
    def author(self) -> str:
        return self._author

    def generate_summary_csv(self, analysis_results: Dict[str, Dict[str, float]], output_path: str) -> None:
        """Write a simple CSV with category, count, avg_engagement."""
        fieldnames = ["category", "count", "avg_engagement"]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for cat, data in analysis_results.items():
                writer.writerow({
                    "category": cat,
                    "count": int(data.get("count", 0)),
                    "avg_engagement": float(data.get("avg_engagement", 0.0)),
                })

    def generate_summary_json(self, analysis_results: Dict[str, Dict[str, float]], output_path: str) -> None:
        """Write analysis_results to a JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis_results, f, indent=2)

    def summarize_semester_findings(self, semester_summary: Dict[str, Dict[str, float]],
                                    trend_changes: Dict[str, Dict[str, float]]) -> str:
        """Return a multi-line human readable summary combining the semester summary and trend changes."""
        lines = [f"Semester Summary — generated by {self._author}", "-" * 40]
        for cat, data in semester_summary.items():
            lines.append(f"{cat}: count={int(data['count'])}, avg_engagement={data['avg_engagement']:.2f}")
            changes = trend_changes.get(cat, {}).get("pct_changes", [])
            if changes:
                last = changes[-1]
                lines.append(f"  Recent week-over-week change: {last:.1f}%")
            else:
                lines.append("  No weekly change data.")
        return "\n".join(lines)

    def __str__(self):
        return f"SemesterReporter(author={self._author!r})"

    def __repr__(self):
        return f"SemesterReporter({self._author!r})"


# -------------------------
# Example usage (run to test)
# -------------------------
if __name__ == "__main__":
    # Create sample posts
    now = int(datetime.utcnow().timestamp())
    p1 = RedditPost("How to learn Python?", "I want advice on learning.", 50, 20, now - 86400 * 10)
    p2 = RedditPost("Breaking announcement: new library", "Major update to the library package", 150, 10, now - 86400 * 20)
    p3 = RedditPost("Funny meme about cats", "lol cats are silly", 20, 5, now - 86400 * 5)

    # Validate
    PostValidator.validate_post_data(p1.to_dict())

    # Categorize
    cat = PostCategorizer()
    print("Categories:", cat.categories)
    print("p1 category:", cat.categorize(p1))
    print("p2 category:", cat.categorize(p2))
    print("p3 category:", cat.categorize(p3))

    # Analyze trends
    analyzer = TrendAnalyzer(cat)
    top = analyzer.get_top_posts([p1, p2, p3], n=2)
    print("Top posts:", top)

    agg = analyzer.aggregate_semester_data([p1, p2, p3])
    print("Aggregate:", agg)

    # Weekly mock data (for compare_trends_over_time)
    weekly = [
        {"question": 5, "news": 2, "meme": 1},
        {"question": 4, "news": 5, "meme": 3},
        {"question": 6, "news": 3, "meme": 2},
    ]
    cmp = analyzer.compare_trends_over_time(weekly)
    print("Trend compare:", cmp)

    # Reporting
    reporter = SemesterReporter(author="Sharon Madu")
    summary_text = reporter.summarize_semester_findings(agg, cmp)
    print("\n" + summary_text)
