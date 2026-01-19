k-concertbook

This is a cleaned copy of the `ticketmaster` project intended for publishing to GitHub.

Included:
- Core Lambda source files for booking, events, tickets, uploads, image handling and SQS worker.
- `python/lambda_function.py` (main handler used for packaging).

Excluded:
- Vendored third-party packages (e.g. `redis`, `requests` folders).
- Build artifacts and archives (zips, `.aws-sam` build, local DynamoDB binary).

Setup
1. Create a Python virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set required environment variables before running or deploying:
- `AWS_*` credentials as usual (or rely on IAM role)
- `OPENSEARCH_URL` (e.g. https://your-opensearch-domain)
- `OPENSEARCH_USER` and `OPENSEARCH_PASS` (if your domain requires basic auth)
- `REDIS_HOST` (optional)

3. Deploy: use AWS SAM / AWS CLI. See each function's comments for details.

Notes
- Sensitive credentials were removed from source. Do NOT commit secrets. Use environment variables or AWS-managed roles.
