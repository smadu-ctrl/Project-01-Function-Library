"""
reddit_analytics_v3.py
Project 3: Advanced OOP Refactor for Reddit Analytics

Features:
- Abstract Base Classes (ABC)
- Inheritance Hierarchies
- Polymorphism
- Composition Relationships
- Compatible with Project 2 analysis


"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
import csv
import statistics
import json

# -------------------------
# ABSTRACT BASE CLASSES
# -------------------------

class AbstractPost(ABC):
    """Abstract base class for all post types."""

    @abstractmethod
    def engagement_score(self) -> int:
        """Return calculated engagement score"""
        pass

    @abstractmethod
    def clean_text(self) -> str:
        """Return cleaned text for analysis"""
        pass


class AbstractCategorizer(ABC):
    """Abstract base class for post categorization."""

    @abstractmethod
    def categorize(self, post: AbstractPost) -> str:
        pass

# -------------------------
# CONCRETE POST CLASSES
# -------------------------

class RedditPost(AbstractPost):
    """Standard Reddit post."""

    def __init__(self, title: str, body: str, score: int, num_comments: int, created_utc: int):
        if not title or not isinstance(title, str):
            raise ValueError("title must be a non-empty string")
        if body is None:
            body = ""
        if not isinstance(score, int) or isinstance(score, bool):
            raise ValueError("score must be an int")
        if not isinstance(num_comments, int) or isinstance(num_comments, bool):
            raise ValueError("num_comments must be an int")
        if not isinstance(created_utc, int) or created_utc < 0:
            raise ValueError("created_utc must be a non-negative int")
        self.title = title
        self.body = body
        self.score = score
        self.num_comments = num_comments
        self.created_utc = created_utc
        self._cleaned_text: Optional[str] = None

    def engagement_score(self, w_upvote=1, w_comment=2) -> int:
        """Calculate standard engagement score."""
        return int(round(self.score * w_upvote + self.num_comments * w_comment))

    def clean_text(self) -> str:
        """Return cleaned text of title + body."""
        if self._cleaned_text is not None:
            return self._cleaned_text
        combined = f"{self.title} {self.body}".lower()
        combined = re.sub(r"[^\w\s]", " ", combined)
        combined = re.sub(r"\s+", " ", combined).strip()
        self._cleaned_text = combined
        return self._cleaned_text

    def format_datetime(self, fmt="%Y-%m-%d %H:%M:%S") -> str:
        dt = datetime.utcfromtimestamp(self.created_utc)
        return dt.strftime(fmt)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "body": self.body,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
            "engagement": self.engagement_score(),
        }

    def __str__(self):
        return f"RedditPost(title={self.title!r}, score={self.score}, comments={self.num_comments})"


class SponsoredPost(RedditPost):
    """Sponsored post with higher comment weight."""

    def engagement_score(self, w_upvote=1, w_comment=3) -> int:
        """Override to weigh comments more heavily."""
        return super().engagement_score(w_upvote, w_comment)


# -------------------------
# CATEGORIZER CLASSES
# -------------------------

class KeywordCategorizer(AbstractCategorizer):
    """Categorizes posts using keyword matching."""

    def __init__(self, categories: Optional[Dict[str, List[str]]] = None):
        default = {
            "question": ["how", "what", "why", "help", "question"],
            "news": ["breaking", "announcement", "news"],
            "discussion": ["discussion", "debate", "opinion"],
            "meme": ["meme", "funny", "lol"],
            "advice": ["advice", "recommend", "should i"],
            "other": [],
        }
        self.categories = categories if categories else default

    def categorize(self, post: AbstractPost) -> str:
        text = post.clean_text()
        hits: Dict[str, int] = {}
        for cat, kws in self.categories.items():
            count = sum(1 for kw in kws if re.search(r"\b" + re.escape(kw) + r"\b", text))
            hits[cat] = count
        best_cat = max(hits.items(), key=lambda kv: kv[1])[0]
        return best_cat if hits[best_cat] > 0 else "other"

    def category_counts(self, posts: List[AbstractPost]) -> Dict[str, int]:
        counts = {c: 0 for c in self.categories.keys()}
        counts.setdefault("other", 0)
        for post in posts:
            cat = self.categorize(post)
            counts.setdefault(cat, 0)
            counts[cat] += 1
        return counts


# -------------------------
# ANALYSIS / TREND CLASSES
# -------------------------

class TrendAnalyzer:
    """Analyzes posts and trends, works with any AbstractPost and AbstractCategorizer."""

    def __init__(self, categorizer: Optional[AbstractCategorizer] = None):
        self.categorizer = categorizer if categorizer else KeywordCategorizer()

    def get_top_posts(self, posts: List[AbstractPost], n=10) -> List[AbstractPost]:
        return sorted(posts, key=lambda p: p.engagement_score(), reverse=True)[:n]

    def filter_posts_by_date(self, posts: List[AbstractPost], start: str, end: str) -> List[AbstractPost]:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        return [p for p in posts if start_ts <= p.created_utc <= end_ts]

    def aggregate_semester_data(self, posts: List[AbstractPost]) -> Dict[str, Dict[str, float]]:
        categories = self.categorizer.categories.keys()
        agg = {c: {"count": 0, "avg_engagement": 0.0} for c in categories}
        agg.setdefault("other", {"count": 0, "avg_engagement": 0.0})
        groups: Dict[str, List[int]] = {c: [] for c in agg.keys()}
        for p in posts:
            cat = self.categorizer.categorize(p)
            groups.setdefault(cat, [])
            groups[cat].append(p.engagement_score())
        for cat, scores in groups.items():
            agg[cat] = {"count": len(scores), "avg_engagement": statistics.mean(scores) if scores else 0.0}
        return agg

    def compare_trends_over_time(self, weekly_data: List[Dict[str, int]]) -> Dict[str, Dict[str, float]]:
        if not weekly_data:
            return {}
        cats = set()
        for wk in weekly_data:
            cats.update(wk.keys())
        result: Dict[str, Dict[str, float]] = {}
        for cat in cats:
            vals = [wk.get(cat, 0) for wk in weekly_data]
            pct_changes = []
            for i in range(1, len(vals)):
                prev, curr = vals[i-1], vals[i]
                pct = ((curr - prev) / prev * 100.0) if prev != 0 else (float("inf") if curr != 0 else 0.0)
                pct_changes.append(pct)
            result[cat] = {"pct_changes": pct_changes, "latest": vals[-1]}
        return result

# -------------------------
# COMPOSITION: COLLECTION OF POSTS
# -------------------------

class RedditCollection:
    """A collection of posts (composition)."""

    def __init__(self):
        self.posts: List[AbstractPost] = []

    def add_post(self, post: AbstractPost):
        self.posts.append(post)

    def top_posts(self, n=5):
        return sorted(self.posts, key=lambda p: p.engagement_score(), reverse=True)[:n]

    def get_category_counts(self, categorizer: AbstractCategorizer) -> Dict[str, int]:
        return categorizer.category_counts(self.posts)


# -------------------------
# REPORTING
# -------------------------

class SemesterReporter:
    """Generate summaries (CSV/JSON/text)"""

    def __init__(self, author: str = "Analyst"):
        self.author = author

    def generate_summary_csv(self, analysis_results: Dict[str, Dict[str, float]], path: str):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["category", "count", "avg_engagement"])
            writer.writeheader()
            for cat, data in analysis_results.items():
                writer.writerow({
                    "category": cat,
                    "count": int(data.get("count", 0)),
                    "avg_engagement": float(data.get("avg_engagement", 0.0)),
                })

    def generate_summary_json(self, analysis_results: Dict[str, Dict[str, float]], path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(analysis_results, f, indent=2)

    def summarize_semester_findings(self, semester_summary, trend_changes) -> str:
        lines = [f"Semester Summary — generated by {self.author}", "-"*40]
        for cat, data in semester_summary.items():
            lines.append(f"{cat}: count={int(data['count'])}, avg_engagement={data['avg_engagement']:.2f}")
            changes = trend_changes.get(cat, {}).get("pct_changes", [])
            if changes:
                lines.append(f"  Recent week-over-week change: {changes[-1]:.1f}%")
            else:
                lines.append("  No weekly change data.")
        return "\n".join(lines)


# -------------------------
# Example Usage
# -------------------------

if __name__ == "__main__":
    now = int(datetime.utcnow().timestamp())
    p1 = RedditPost("How to learn Python?", "Advice needed", 50, 20, now - 86400*10)
    p2 = RedditPost("Breaking: New library update", "Details inside", 150, 10, now - 86400*20)
    p3 = SponsoredPost("Buy our product!", "Limited offer", 30, 5, now - 86400*5)

    collection = RedditCollection()
    for post in [p1, p2, p3]:
        collection.add_post(post)

    cat = KeywordCategorizer()
    analyzer = TrendAnalyzer(cat)

    print("Top posts:", collection.top_posts(2))
    agg = analyzer.aggregate_semester_data(collection.posts)
    weekly = [{"question": 5, "news": 2, "meme": 1}, {"question": 4, "news": 5, "meme": 3}]
    trends = analyzer.compare_trends_over_time(weekly)

    reporter = SemesterReporter(author="Sharon Madu")
    summary_text = reporter.summarize_semester_findings(agg, trends)
    print("\n" + summary_text)
