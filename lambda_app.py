import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
import os
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

import boto3

from src.analysis.detect_shocks import main as detect_shocks_main
from src.analysis.explain_shocks import main as explain_shocks_main
from src.analysis.plot_heating_oil_shocks import main as plot_shocks_main

s3 = boto3.client("s3")

BUCKET_NAME = os.environ["BUCKET_NAME"]
S3_PREFIX = os.environ.get("S3_PREFIX", "dev/globalshock")


def upload_file(local_path: str, s3_key: str, content_type: str | None = None) -> None:
    extra = {}
    if content_type:
        extra["ContentType"] = content_type

    s3.upload_file(local_path, BUCKET_NAME, s3_key, ExtraArgs=extra)


def lambda_handler(event, context):
    try:
        project_root = Path(__file__).resolve().parent
        os.chdir(project_root)

        detect_shocks_main()
        explain_shocks_main()
        plot_shocks_main()

        outputs = [
            ("data/out/heating_oil_shocks.png", f"{S3_PREFIX}/outputs/heating_oil_shocks.png", "image/png"),
            ("reports/shocks_report.md", f"{S3_PREFIX}/reports/shocks_report.md", "text/markdown"),
            ("data/sample/heating_oil_shocks.csv", f"{S3_PREFIX}/processed/heating_oil_shocks.csv", "text/csv"),
            ("data/sample/heating_oil_gbp_real.ndjson", f"{S3_PREFIX}/processed/heating_oil_gbp_real.ndjson", "application/x-ndjson"),
        ]

        uploaded = []
        for local_path, s3_key, content_type in outputs:
            if Path(local_path).exists():
                upload_file(local_path, s3_key, content_type)
                uploaded.append({"local": local_path, "s3": s3_key})

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "ok",
                    "ran_at": datetime.now(timezone.utc).isoformat(),
                    "uploaded": uploaded,
                }
            ),
        }

    except Exception as exc:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            ),
        }