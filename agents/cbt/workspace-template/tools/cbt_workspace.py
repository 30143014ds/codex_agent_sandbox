#!/usr/bin/env python3
"""Local CBT scoring and continuity. Python 3.11+, standard library, POSIX."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from uuid import uuid4
from zoneinfo import ZoneInfo


KINDS = {"session": "sessions", "thought-record": "thought-records", "activity": "activities",
         "experiment": "experiments", "review": "reviews", "safety": "safety"}
STATUSES = {"in_progress", "paused", "completed", "declined"}
DISTORTIONS = {"all_or_nothing", "overgeneralization", "mental_filter", "disqualifying_positive",
               "jumping_to_conclusions", "magnification_minimization", "emotional_reasoning",
               "should_statements", "labeling", "personalization"}
ASSESSMENT_KEYS = {"instrument_id", "status", "answers", "recorded_at", "attempt_id",
                   "supersedes", "context", "window_start", "window_end",
                   "presentation_language", "presented_wording"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reject_constant(_):
    raise ValueError("JSON must not contain NaN or infinity")


def decode(text):
    return json.loads(text, parse_constant=reject_constant)


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"


def timestamp(value=None):
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    require(isinstance(value, str), "Timestamp must be an offset-aware ISO string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(dt.tzinfo is not None and dt.utcoffset() is not None, "Timestamp needs a UTC offset")
    return dt.isoformat(timespec="microseconds")


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,119}", value),
            "Invalid record identifier")
    return value


def rating(value):
    require(value is None or (type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100),
            "Ratings must be finite numbers from 0 to 100, or null")


def validate_thought(thought, completed):
    require(isinstance(thought, dict), "thought_record must be an object")
    if completed:
        for key in ("situation", "automatic_thought"):
            require(isinstance(thought.get(key), str) and thought[key].strip(),
                    "Completed thought records need a situation and automatic thought")
    for key in ("belief_before", "belief_after"):
        if key in thought:
            rating(thought[key])
    emotions = thought.get("emotions", {})
    require(isinstance(emotions, dict) and not set(emotions) - {"before", "after"},
            "emotions must contain before/after objects")
    for values in emotions.values():
        require(isinstance(values, dict), "Emotion ratings must be named objects")
        for name, value in values.items():
            require(isinstance(name, str) and name.strip(), "An emotion needs a name")
            rating(value)
    for key in ("evidence_for", "evidence_against", "physical_sensations", "core_beliefs"):
        if key in thought:
            require(isinstance(thought[key], list) and all(isinstance(x, str) for x in thought[key]),
                    f"{key} must be a string array")
    for key in ("situation", "automatic_thought", "behavior", "alternative_thought", "safety_behavior"):
        if key in thought:
            require(thought[key] is None or isinstance(thought[key], str), f"{key} must be text or null")
    distortions = thought.get("cognitive_distortions", [])
    require(isinstance(distortions, list), "cognitive_distortions must be an array")
    for entry in distortions:
        require(isinstance(entry, dict) and entry.get("category") in DISTORTIONS
                and entry.get("status") in ("tentative", "agreed"), "Invalid distortion hypothesis")
        subtype = entry.get("subtype")
        require(subtype is None or (entry["category"] == "jumping_to_conclusions"
                and subtype in ("mind_reading", "fortune_telling")), "Invalid distortion subtype")


class Workspace:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve(strict=True)
        self.settings = decode(self.safe("settings.json").read_text(encoding="utf-8"))
        require(self.settings.get("workspace_kind") == "burns-cbt"
                and self.settings.get("schema_version") == 1, "Not a supported CBT workspace")
        storage = self.settings.get("storage")
        require(isinstance(storage, dict) and all(type(storage.get(k)) is bool for k in
                ("enabled", "session_summaries", "exercise_records", "assessment_history", "full_transcripts")),
                "Storage preferences must be explicit booleans")
        cadence = self.settings.get("cadence_days")
        require(isinstance(cadence, dict) and all(type(n) is int and n > 0 for n in cadence.values()),
                "Cadence must contain positive integer day counts")
        require("review" in cadence, "A review cadence is required")
        self.tz = ZoneInfo(self.settings["timezone"]) if self.settings.get("timezone") else None

    def safe(self, *parts):
        path = self.root.joinpath(*parts)
        require(path.is_relative_to(self.root), "Path escapes workspace")
        for parent in (path, *path.parents):
            if parent == self.root:
                break
            require(not parent.is_symlink(), "Symlinked journal/resource paths are not supported")
        require(path.resolve().is_relative_to(self.root), "Path escapes workspace")
        return path

    def local_date(self, value):
        dt = datetime.fromisoformat(timestamp(value))
        return dt.astimezone(self.tz).date() if self.tz else dt.astimezone().date()

    def instrument(self, instrument_id):
        identifier(instrument_id)
        path = self.safe("resources", "instruments", instrument_id + ".json")
        definition = decode(path.read_text(encoding="utf-8"))
        require(definition.get("instrument_id") == instrument_id, "Instrument identity mismatch")
        count = definition.get("item_count")
        require(type(count) is int and count > 0, "Invalid instrument length")
        require([x.get("id") for x in definition["items"]] == list(range(1, count + 1)),
                "Instrument items must have consecutive stable IDs")
        values = definition.get("answer_values")
        require(isinstance(values, list) and values and all(type(x) is int for x in values)
                and len(values) == len(set(values)), "Invalid response values")
        require([x.get("value") for x in definition["anchors"]] == values, "Anchor/value mismatch")
        require(all(type(x) is int and 1 <= x <= count for x in definition.get("safety_items", [])),
                "Invalid safety item IDs")
        if definition.get("scoring") == "sum":
            bands = definition["bands"]
            expected = count * min(values)
            for band in bands:
                require(band["min"] == expected and band["max"] >= band["min"],
                        "Instrument bands must be consecutive and nonoverlapping")
                expected = band["max"] + 1
            require(expected == count * max(values) + 1, "Instrument bands must cover the scale")
        elif definition.get("scoring") == "domains":
            items = [i for domain in definition["domains"] for i in domain["items"]]
            require(sorted(items) == list(range(1, count + 1)), "Domains must cover each item once")
        else:
            raise ValueError("Unsupported scoring rule")
        fingerprint = hashlib.sha256(json.dumps(definition, sort_keys=True, ensure_ascii=False,
                                                separators=(",", ":")).encode("utf-8")).hexdigest()
        return definition, fingerprint

    def score(self, payload):
        require(isinstance(payload, dict) and not set(payload) - ASSESSMENT_KEYS,
                "Assessment input contains unsupported fields")
        definition, fingerprint = self.instrument(payload["instrument_id"])
        status = payload.get("status")
        require(status in ("completed", "partial", "declined"), "Invalid assessment status")
        answers = payload.get("answers")
        require(isinstance(answers, list) and len(answers) == definition["item_count"],
                "Provide a full-length answer array; use null for unanswered items")
        require(all(x is None or (type(x) is int and x in definition["answer_values"]) for x in answers),
                "Answers must be allowed integer values or null, not booleans")
        require(status != "completed" or all(x is not None for x in answers),
                "Completed assessments cannot have missing items")
        require(status != "declined" or all(x is None for x in answers),
                "A declined attempt cannot contain answers; use partial instead")
        context = payload.get("context")
        require(context is None or isinstance(context, str), "Context must be text or null")
        language = payload.get("presentation_language", "en")
        require(isinstance(language, str) and re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language),
                "Presentation language must be a language tag such as en or ru")
        wording = payload.get("presented_wording")
        require(wording is None or isinstance(wording, dict), "Presented wording must be an object or null")
        if language != "en" and status != "declined":
            require(isinstance(wording, dict), "Translated attempts must retain the wording used")
        if wording is not None:
            require(not set(wording) - {"items", "anchors"}, "Unsupported presented-wording fields")
            items = wording.get("items", {})
            require(isinstance(items, dict) and all(k in {str(i) for i in range(1, len(answers) + 1)}
                    and isinstance(v, str) and v.strip() for k, v in items.items()),
                    "Presented items must map valid item IDs to nonempty text")
            anchors = wording.get("anchors")
            require(isinstance(anchors, list) and len(anchors) == len(definition["anchors"])
                    and all(isinstance(v, str) and v.strip() for v in anchors), "Retain all presented response anchors")
            require(all(answer is None or str(i) in items for i, answer in enumerate(answers, 1)),
                    "Retain translated wording for every answered item")
        recorded = timestamp(payload.get("recorded_at"))
        window = dict(definition["window"])
        if window["type"] == "past_week_including_today":
            require((payload.get("window_start") is None) == (payload.get("window_end") is None),
                    "Provide both observation-window dates or neither")
            end = date.fromisoformat(payload["window_end"]) if payload.get("window_end") else self.local_date(recorded)
            start = date.fromisoformat(payload["window_start"]) if payload.get("window_start") else end - timedelta(days=6)
            require((end - start).days == 6 and end <= self.local_date(recorded),
                    "Depression window must cover seven calendar days and end no later than recording")
            window.update(start=start.isoformat(), end=end.isoformat())
        else:
            require(payload.get("window_start") is None and payload.get("window_end") is None,
                    "This instrument does not use a dated symptom window")
        total = band = domains = None
        if status == "completed":
            if definition["scoring"] == "sum":
                total = sum(answers)
                band = next(b for b in definition["bands"] if b["min"] <= total <= b["max"])
            else:
                domains = {d["id"]: sum(answers[i - 1] for i in d["items"]) for d in definition["domains"]}
        safety_ids = definition.get("safety_items", [])
        positive = [i for i in safety_ids if answers[i - 1] is not None and answers[i - 1] > 0]
        return {"schema_version": 1, "instrument_id": definition["instrument_id"],
                "instrument_hash": fingerprint, "source": definition["source"], "status": status,
                "recorded_at": recorded, "observation_window": window, "answers": answers,
                "answered_count": sum(x is not None for x in answers), "total": total,
                "book_band": band, "domains": domains, "context": context,
                "presentation_language": language, "presented_wording": wording,
                "safety": {"positive_answer_items": positive,
                           "unanswered_items": [i for i in safety_ids if answers[i - 1] is None],
                           "follow_up": "direct_conversation_required" if positive else "safety_not_established_by_score"}}

    def storage_allowed(self, category):
        settings = self.settings["storage"]
        require(settings["enabled"] and settings[category], "Saving is disabled by workspace preferences")

    @contextmanager
    def locked(self):
        fd = os.open(self.safe(".cbt.lock"), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def atomic_write(self, path, content):
        self.safe(*path.relative_to(self.root).parts)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        fd, temporary = tempfile.mkstemp(prefix=".cbt-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def events(self):
        path = self.safe("assessments", "results.jsonl")
        if not path.exists():
            return []
        rows, latest, event_ids = [], {}, set()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                require(bool(line.strip()), "Blank journal entry")
                row = decode(line)
                identifier(row["event_id"])
                identifier(row["attempt_id"])
                previous = latest.get(row["attempt_id"])
                require(row["event_id"] not in event_ids, "Duplicate journal event")
                require(row.get("supersedes") == (previous["event_id"] if previous else None),
                        "Broken assessment revision chain")
                if previous:
                    require(row["instrument_id"] == previous["instrument_id"]
                            and row["instrument_hash"] == previous["instrument_hash"],
                            "Assessment revision changed instrument/version")
                # Verify the current-version raw answers and computed fields before analytics.
                _, current_hash = self.instrument(row["instrument_id"])
                if row["instrument_hash"] == current_hash:
                    raw = {key: row[key] for key in ("instrument_id", "status", "answers", "recorded_at", "context",
                                                    "presentation_language", "presented_wording")}
                    window = row["observation_window"]
                    if window.get("start"):
                        raw.update(window_start=window["start"], window_end=window["end"])
                    recomputed = self.score(raw)
                    require(all(row[k] == recomputed[k] for k in
                                ("total", "book_band", "domains", "safety", "answered_count", "observation_window")),
                            "Stored score disagrees with raw answers")
                event_ids.add(row["event_id"])
                latest[row["attempt_id"]] = row
                rows.append(row)
            except (ValueError, KeyError, TypeError, StopIteration) as exc:
                raise ValueError(f"Invalid assessment journal entry at line {number}; no data changed") from exc
        return rows

    def latest_attempts(self):
        latest = {}
        for row in self.events():
            latest[row["attempt_id"]] = row
        return list(latest.values())

    def save_assessment(self, payload):
        self.storage_allowed("assessment_history")
        scored = self.score(payload)
        attempt_id = identifier(payload.get("attempt_id") or "attempt-" + uuid4().hex)
        with self.locked():
            latest = next((r for r in self.latest_attempts() if r["attempt_id"] == attempt_id), None)
            require(payload.get("supersedes") == (latest["event_id"] if latest else None),
                    "A revision must supersede the latest event; stale or missing revision")
            if latest:
                require(latest["instrument_id"] == scored["instrument_id"]
                        and latest["instrument_hash"] == scored["instrument_hash"],
                        "A revision cannot change the instrument/version")
            scored.update(event_id="assessment-" + uuid4().hex, attempt_id=attempt_id,
                          supersedes=payload.get("supersedes"), saved_at=timestamp())
            path = self.safe("assessments", "results.jsonl")
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            require(not old or old.endswith("\n"), "Journal has an incomplete final line; no data changed")
            self.atomic_write(path, old + json.dumps(scored, ensure_ascii=False, allow_nan=False) + "\n")
        return scored

    def read_note_path(self, path):
        text = path.read_text(encoding="utf-8")
        require(text.startswith("---\n"), "Note is missing structured frontmatter")
        header, delimiter, body = text[4:].partition("\n---\n")
        require(bool(delimiter), "Note frontmatter is incomplete")
        note = decode(header)
        require(note["kind"] in KINDS and note["status"] in STATUSES, "Invalid note kind/status")
        require(note["id"] == path.stem and path.parent.name == KINDS[note["kind"]], "Note identity/path mismatch")
        timestamp(note["created_at"])
        timestamp(note["updated_at"])
        return {**note, "content": body.rstrip("\n")}

    def read_note(self, record_id):
        identifier(record_id)
        matches = [self.safe(folder, record_id + ".md") for folder in KINDS.values()]
        matches = [p for p in matches if p.exists()]
        require(len(matches) == 1, "Record not found or record ID is ambiguous")
        return self.read_note_path(matches[0])

    def save_note(self, payload):
        allowed = {"kind", "status", "title", "content", "metadata", "record_id", "expected_updated_at"}
        require(isinstance(payload, dict) and not set(payload) - allowed, "Unsupported note input fields")
        kind, status = payload.get("kind"), payload.get("status")
        require(kind in KINDS and status in STATUSES, "Invalid note kind/status")
        self.storage_allowed("session_summaries" if kind == "session" else "exercise_records")
        for key in ("title", "content"):
            require(isinstance(payload.get(key), str) and payload[key].strip(), f"A note needs {key}")
        metadata = payload.get("metadata", {})
        require(isinstance(metadata, dict), "Metadata must be an object")
        # Round-trip also rejects non-JSON/nonfinite metadata from direct Python callers.
        metadata = decode(encode(metadata))
        if kind == "thought-record":
            require("thought_record" in metadata, "Thought-record notes need structured thought_record metadata")
        if "thought_record" in metadata:
            validate_thought(metadata["thought_record"], status == "completed")
        now = timestamp()
        with self.locked():
            old = None
            record_id = payload.get("record_id")
            if record_id:
                old = self.read_note(record_id)
                require(old["kind"] == kind and payload.get("expected_updated_at") == old["updated_at"],
                        "Note update is stale or changes kind")
                created = old["created_at"]
            else:
                require(payload.get("expected_updated_at") is None, "New notes cannot specify an expected update")
                record_id = self.local_date(now).isoformat() + "-" + kind + "-" + uuid4().hex[:16]
                created = now
            completed_at = None
            if status == "completed":
                completed_at = (old.get("completed_at") or now) if old and old["status"] == "completed" else now
            header = {"schema_version": 1, "id": record_id, "kind": kind, "status": status,
                      "title": payload["title"], "created_at": created, "updated_at": now,
                      "completed_at": completed_at, "metadata": metadata}
            path = self.safe(KINDS[kind], record_id + ".md")
            require(payload.get("record_id") is not None or not path.exists(), "Record ID collision")
            self.atomic_write(path, "---\n" + encode(header).rstrip() + "\n---\n" + payload["content"].rstrip() + "\n")
        return {**header, "path": str(path.relative_to(self.root))}

    def comparable(self, instrument_id):
        _, fingerprint = self.instrument(instrument_id)
        rows = [r for r in self.latest_attempts() if r["instrument_id"] == instrument_id]
        comparable = sorted((r for r in rows if r["status"] == "completed" and r["instrument_hash"] == fingerprint),
                            key=lambda r: (self.measurement_date(r), datetime.fromisoformat(r["recorded_at"])))
        return comparable, sum(r["instrument_hash"] != fingerprint for r in rows)

    def measurement_date(self, row):
        end = row["observation_window"].get("end")
        return date.fromisoformat(end) if end else self.local_date(row["recorded_at"])

    def trend(self, instrument_id):
        rows, excluded = self.comparable(instrument_id)
        series = {}
        for language in sorted({r["presentation_language"] for r in rows}):
            group = [r for r in rows if r["presentation_language"] == language]
            points = [{k: r[k] for k in ("attempt_id", "recorded_at", "observation_window", "total", "domains")}
                      for r in group]
            delta = group[-1]["total"] - group[0]["total"] if len(group) > 1 and group[0]["total"] is not None else None
            series[language] = {"points": points, "last_minus_first": delta}
        return {"instrument_id": instrument_id, "completed_attempts": len(rows), "series": series,
                "excluded_version_mismatches": excluded,
                "interpretation": "Descriptive within-person observations; no diagnosis, causality or reliable-change claim."}

    def due(self, as_of=None):
        today = date.fromisoformat(as_of) if as_of else self.local_date(timestamp())
        output = {}
        for instrument_id, days in self.settings["cadence_days"].items():
            if instrument_id == "review":
                continue
            rows, excluded = self.comparable(instrument_id)
            rows = [r for r in rows if self.measurement_date(r) <= today]
            last = max((self.measurement_date(r) for r in rows), default=None)
            next_date = last + timedelta(days=days) if last else None
            output[instrument_id] = {"last_completed": last.isoformat() if last else None,
                                     "next_due": next_date.isoformat() if next_date else None,
                                     "due": next_date is None or today >= next_date,
                                     "reason": "baseline_not_completed" if last is None else "periodic",
                                     "excluded_version_mismatches": excluded}
        review_dates = []
        directory = self.safe("reviews")
        if directory.exists():
            for path in directory.glob("*.md"):
                self.safe("reviews", path.name)
                note = self.read_note_path(path)
                day = self.local_date(note.get("completed_at") or note["updated_at"])
                if note["status"] == "completed" and day <= today:
                    review_dates.append(day)
        start = self.settings.get("review_started_at")
        if start:
            start = date.fromisoformat(start)
            require(start <= today, "Review baseline cannot be after the requested current date")
            review_dates.append(start)
        last_review = max(review_dates, default=None)
        next_review = last_review + timedelta(days=self.settings["cadence_days"]["review"]) if last_review else None
        output["review"] = {"last_review_or_baseline": last_review.isoformat() if last_review else None,
                            "next_due": next_review.isoformat() if next_review else None,
                            "due": next_review is not None and today >= next_review,
                            "reason": "first_review_pending" if last_review is None else "periodic"}
        return {"as_of": today.isoformat(), "schedule": output, "background_notifications": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Marked CBT workspace directory")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list-instruments")
    instrument = sub.add_parser("instrument")
    instrument.add_argument("instrument_id")
    for command in ("score", "save-assessment", "save-note"):
        p = sub.add_parser(command)
        p.add_argument("--input", required=True, help="JSON file, or - for stdin")
    read = sub.add_parser("read-note")
    read.add_argument("--record-id", required=True)
    trend = sub.add_parser("trend")
    trend.add_argument("--instrument", required=True)
    due = sub.add_parser("due")
    due.add_argument("--as-of", help="Optional local calendar date YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        workspace = Workspace(args.workspace)
        if args.command in ("score", "save-assessment", "save-note"):
            raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
            payload = decode(raw)
            result = {"score": workspace.score, "save-assessment": workspace.save_assessment,
                      "save-note": workspace.save_note}[args.command](payload)
        elif args.command == "instrument":
            result = workspace.instrument(args.instrument_id)[0]
        elif args.command == "list-instruments":
            directory = workspace.safe("resources", "instruments")
            result = [{k: workspace.instrument(p.stem)[0][k] for k in ("instrument_id", "name", "item_count")}
                      for p in sorted(directory.glob("*.json"))]
        elif args.command == "read-note":
            result = workspace.read_note(args.record_id)
        elif args.command == "trend":
            result = workspace.trend(args.instrument)
        else:
            result = workspace.due(args.as_of)
        sys.stdout.write(encode(result))
        return 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        # Validation messages never include raw answers or note bodies.
        sys.stderr.write(f"CBT workspace error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
