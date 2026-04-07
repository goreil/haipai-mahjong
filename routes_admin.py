#!/usr/bin/env python3
"""Admin routes: user stats, feedback management, GitHub issue creation."""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from functools import wraps
import os
import sys

import db
import requests as http_requests

admin_bp = Blueprint("admin", __name__)


def require_admin(f):
    """Decorator that checks current_user is an admin."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        from app import get_conn
        conn = get_conn()
        if not db.is_admin(conn, current_user.id):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


# --- User feedback submission ---

@admin_bp.route("/api/feedback", methods=["POST"])
@login_required
def api_feedback():
    from app import get_conn
    conn = get_conn()
    uid = current_user.id
    body = request.json or {}
    fb_type = body.get("type", "general")
    if fb_type not in ("bug", "feature", "general"):
        return jsonify({"error": "type must be bug, feature, or general"}), 400
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long (max 2000 chars)"}), 400
    conn.execute(
        "INSERT INTO feedback (user_id, type, message) VALUES (?, ?, ?)",
        (uid, fb_type, message),
    )
    conn.commit()

    # Discord webhook notification
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if discord_url:
        try:
            http_requests.post(discord_url, json={
                "content": f"**New feedback** ({fb_type}) from {current_user.username}:\n>>> {message[:500]}"
            }, timeout=5)
        except Exception:
            pass  # Non-critical

    return jsonify({"ok": True})


@admin_bp.route("/api/feedback/mine")
@login_required
def api_feedback_mine():
    from app import get_conn
    conn = get_conn()
    items = db.get_user_feedback(conn, current_user.id)
    return jsonify(items)


# --- Admin endpoints ---

@admin_bp.route("/api/admin/stats")
@require_admin
def api_admin_stats():
    from app import get_conn
    conn = get_conn()
    users = db.admin_user_stats(conn)
    return jsonify({"users": users, "total_users": len(users)})


@admin_bp.route("/api/admin/feedback")
@require_admin
def api_admin_feedback():
    from app import get_conn
    conn = get_conn()
    status = request.args.get("status")
    fb_type = request.args.get("type")
    items = db.list_feedback(conn, status=status, fb_type=fb_type)
    return jsonify(items)


@admin_bp.route("/api/admin/feedback/<int:feedback_id>", methods=["POST"])
@require_admin
def api_admin_feedback_update(feedback_id):
    from app import get_conn
    conn = get_conn()
    body = request.json or {}
    status = body.get("status")
    admin_note = body.get("admin_note")

    if status and status not in ("new", "in-progress", "resolved"):
        return jsonify({"error": "Invalid status"}), 400
    if admin_note is not None and len(admin_note) > 2000:
        return jsonify({"error": "Note too long"}), 400

    updates = {}
    if status:
        updates["status"] = status
    if admin_note is not None:
        updates["admin_note"] = admin_note

    if not updates:
        return jsonify({"error": "Nothing to update"}), 400

    item = db.get_feedback_item(conn, feedback_id)
    if not item:
        return jsonify({"error": "Feedback not found"}), 404

    db.update_feedback(conn, feedback_id, **updates)
    return jsonify({"ok": True})


@admin_bp.route("/api/admin/feedback/<int:feedback_id>/create-issue", methods=["POST"])
@require_admin
def api_admin_create_issue(feedback_id):
    from app import get_conn
    conn = get_conn()
    item = db.get_feedback_item(conn, feedback_id)
    if not item:
        return jsonify({"error": "Feedback not found"}), 404
    if item.get("github_issue_url"):
        return jsonify({"error": "Issue already created", "url": item["github_issue_url"]}), 409

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return jsonify({"error": "GITHUB_TOKEN not configured"}), 500

    repo = os.environ.get("GITHUB_REPO", "goreil/haipai-mahjong")

    label_map = {"bug": "bug", "feature": "enhancement", "general": "feedback"}
    labels = ["feedback"]
    type_label = label_map.get(item["type"])
    if type_label and type_label != "feedback":
        labels.append(type_label)

    title = f"[feedback] {item['type']}: {item['message'][:60]}"
    body = (
        f"**From**: {item['username']}\n"
        f"**Type**: {item['type']}\n"
        f"**Date**: {item['created_at']}\n\n"
        f"---\n\n{item['message']}\n\n"
        f"---\n*Feedback ID: {feedback_id}*"
    )

    try:
        resp = http_requests.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={"title": title, "body": body, "labels": labels},
            timeout=10,
        )
        resp.raise_for_status()
        issue_url = resp.json().get("html_url", "")
    except http_requests.RequestException as e:
        return jsonify({"error": f"GitHub API error: {e}"}), 502

    db.update_feedback(conn, feedback_id, github_issue_url=issue_url, status="in-progress")
    return jsonify({"ok": True, "url": issue_url})
