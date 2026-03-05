"""AWS CDK stack for Intelligent Document Processing infrastructure."""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct


class IdpStack(Stack):
    """CDK stack that provisions the S3 bucket for document storage.

    This stack does NOT create any new IAM roles. The application uses the
    existing 'GxPEC2-role' which has full admin access. The role is imported
    here only for reference/output purposes.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for document storage and BDA output
        self.document_bucket = s3.Bucket(
            self,
            "DocumentBucket",
            bucket_name="ntkey-idp-documents",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="AbortIncompleteMultipart",
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                ),
                s3.LifecycleRule(
                    id="ExpireBDAOutput",
                    prefix="bda-output/",
                    expiration=Duration.days(90),
                ),
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.GET,
                    ],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                ),
            ],
        )

        # Do NOT create any new IAM roles. The application uses the existing
        # 'GxPEC2-role' which has full admin access to all AWS services
        # including S3, Bedrock, and Bedrock Data Automation.
        existing_role = iam.Role.from_role_name(
            self, "ExistingRole", "GxPEC2-role"
        )

        # Outputs
        CfnOutput(
            self,
            "DocumentBucketName",
            value=self.document_bucket.bucket_name,
            description="S3 bucket name for document storage",
        )

        CfnOutput(
            self,
            "DocumentBucketArn",
            value=self.document_bucket.bucket_arn,
            description="S3 bucket ARN for document storage",
        )

        CfnOutput(
            self,
            "ExistingRoleName",
            value=existing_role.role_name,
            description=(
                "Existing IAM role used by the application. "
                "No new roles are created by this stack."
            ),
        )
