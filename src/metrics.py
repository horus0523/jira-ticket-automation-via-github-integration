from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Response

# Prometheus metrics for webhook processing observability
webhooks_received = Counter(
    "webhooks_received_total", "Total webhooks received", ["source"]
)

jira_tickets_created = Counter(
    "jira_tickets_created_total", "Total Jira tickets created successfully", ["result"]
)

webhook_processing_time = Histogram(
    "webhook_processing_seconds", "Time spent processing webhooks", ["command_type"]
)


def metrics_endpoint():
    """Expose /metrics endpoint for Prometheus scraping."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
