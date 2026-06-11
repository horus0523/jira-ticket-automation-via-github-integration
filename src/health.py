from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    # Returns service status for load balancer/orchestrator health checks
    return jsonify(
        {
            "status": "ok",
            "service": "jira-webhook-service",
            "version": current_app.config.get("VERSION", "1.0.0"),
        }
    )
