"""AWS Lambda Function URL entry point."""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
