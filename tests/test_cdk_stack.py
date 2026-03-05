"""Tests for the CDK infrastructure stack."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock aws_cdk and constructs since they are not installed in test env.
# We build a lightweight mock layer that captures CDK construct calls
# so we can verify the CloudFormation template structure.


def _build_cdk_mocks():
    """Build mock modules for aws_cdk and constructs."""
    constructs_mod = MagicMock()

    # Core CDK mocks
    cdk_mod = MagicMock()

    # Duration mock
    duration_mock = MagicMock()
    duration_mock.days = lambda n: {"days": n}
    cdk_mod.Duration = duration_mock

    # RemovalPolicy mock
    cdk_mod.RemovalPolicy.DESTROY = "DESTROY"
    cdk_mod.RemovalPolicy.RETAIN = "RETAIN"

    # Stack mock - make it a real class
    class MockStack:
        def __init__(self, scope, construct_id, **kwargs):
            self.scope = scope
            self.construct_id = construct_id
            self.node = MagicMock()
            self._resources = {}
            self._outputs = {}

    cdk_mod.Stack = MockStack

    # CfnOutput tracking
    outputs_created = []

    class MockCfnOutput:
        def __init__(self, scope, id, *, value="", description="", **kwargs):
            self.id = id
            self.value = value
            self.description = description
            outputs_created.append({"id": id, "value": value, "description": description})

    cdk_mod.CfnOutput = MockCfnOutput

    # S3 mocks
    s3_mod = MagicMock()
    buckets_created = []

    class MockBucket:
        def __init__(self, scope, id, **kwargs):
            self.id = id
            self.props = kwargs
            self.bucket_name = kwargs.get("bucket_name", "")
            self.bucket_arn = f"arn:aws:s3:::{self.bucket_name}"
            buckets_created.append(self)

    s3_mod.Bucket = MockBucket
    s3_mod.BlockPublicAccess.BLOCK_ALL = "BLOCK_ALL"
    s3_mod.HttpMethods.PUT = "PUT"
    s3_mod.HttpMethods.POST = "POST"
    s3_mod.HttpMethods.GET = "GET"
    s3_mod.LifecycleRule = lambda **kwargs: kwargs
    s3_mod.CorsRule = lambda **kwargs: kwargs

    cdk_mod.aws_s3 = s3_mod

    # IAM mocks
    iam_mod = MagicMock()
    roles_created = []
    roles_imported = []

    class MockRole:
        def __init__(self, scope, id, **kwargs):
            self.id = id
            self.props = kwargs
            self.role_name = kwargs.get("role_name", "")
            roles_created.append(self)

        @staticmethod
        def from_role_name(scope, id, role_name):
            ref = MagicMock()
            ref.role_name = role_name
            ref._imported = True
            roles_imported.append({"id": id, "role_name": role_name})
            return ref

    iam_mod.Role = MockRole
    cdk_mod.aws_iam = iam_mod

    # Environment mock
    cdk_mod.Environment = lambda **kwargs: kwargs

    # App mock
    class MockApp:
        def __init__(self, **kwargs):
            self.node = MagicMock()

        def synth(self):
            pass

    cdk_mod.App = MockApp

    return {
        "cdk_mod": cdk_mod,
        "constructs_mod": constructs_mod,
        "s3_mod": s3_mod,
        "iam_mod": iam_mod,
        "buckets_created": buckets_created,
        "roles_created": roles_created,
        "roles_imported": roles_imported,
        "outputs_created": outputs_created,
        "MockApp": MockApp,
    }


def _install_mocks(mocks):
    """Install mock modules into sys.modules."""
    sys.modules["aws_cdk"] = mocks["cdk_mod"]
    sys.modules["constructs"] = mocks["constructs_mod"]
    sys.modules["aws_cdk.aws_s3"] = mocks["s3_mod"]
    sys.modules["aws_cdk.aws_iam"] = mocks["iam_mod"]


def _cleanup_mocks():
    """Remove mock modules from sys.modules."""
    for mod_name in ["aws_cdk", "constructs", "aws_cdk.aws_s3", "aws_cdk.aws_iam"]:
        sys.modules.pop(mod_name, None)
    # Also remove cached imports of our stack module
    for key in list(sys.modules.keys()):
        if "idp_stack" in key:
            del sys.modules[key]


def _import_stack():
    """Import IdpStack after mocks are installed."""
    # Add cdk directory to path so stacks package can be found
    cdk_dir = str(Path(__file__).parent.parent / "cdk")
    if cdk_dir not in sys.path:
        sys.path.insert(0, cdk_dir)
    from stacks.idp_stack import IdpStack
    return IdpStack


def test_s3_bucket_created_with_correct_name():
    """Test that an S3 bucket is created with name 'ntkey-idp-documents'."""
    mocks = _build_cdk_mocks()
    _install_mocks(mocks)
    try:
        IdpStack = _import_stack()
        app = mocks["MockApp"]()
        IdpStack(app, "TestStack")

        buckets = mocks["buckets_created"]
        assert len(buckets) >= 1, "Expected at least one S3 bucket to be created"

        bucket_names = [b.bucket_name for b in buckets]
        assert "ntkey-idp-documents" in bucket_names, (
            f"Expected bucket 'ntkey-idp-documents', got {bucket_names}"
        )

        # Verify bucket name starts with ntkey-
        for b in buckets:
            if b.bucket_name == "ntkey-idp-documents":
                assert b.bucket_name.startswith("ntkey-"), (
                    "Bucket name must start with 'ntkey-'"
                )
                # Verify versioning
                assert b.props.get("versioned") is True, "Bucket should be versioned"
                # Verify block public access
                assert b.props.get("block_public_access") == "BLOCK_ALL", (
                    "Bucket should block all public access"
                )
                # Verify removal policy
                assert b.props.get("removal_policy") == "DESTROY", (
                    "Bucket should have DESTROY removal policy"
                )
                # Verify auto delete
                assert b.props.get("auto_delete_objects") is True, (
                    "Bucket should have auto_delete_objects=True"
                )
                break
    finally:
        _cleanup_mocks()


def test_no_iam_role_created():
    """Test that no new IAM role is created - we use existing GxPEC2-role."""
    mocks = _build_cdk_mocks()
    _install_mocks(mocks)
    try:
        IdpStack = _import_stack()
        app = mocks["MockApp"]()
        IdpStack(app, "TestStack")

        # No new IAM roles should be created (only imported)
        assert len(mocks["roles_created"]) == 0, (
            f"No new IAM roles should be created, but found {len(mocks['roles_created'])}"
        )

        # Verify existing role is imported
        assert len(mocks["roles_imported"]) >= 1, (
            "Expected at least one role to be imported via from_role_name"
        )
        imported_role_names = [r["role_name"] for r in mocks["roles_imported"]]
        assert "GxPEC2-role" in imported_role_names, (
            f"Expected 'GxPEC2-role' to be imported, got {imported_role_names}"
        )
    finally:
        _cleanup_mocks()


def test_cfn_outputs_exist():
    """Test that CfnOutputs are created for bucket name, ARN, and role."""
    mocks = _build_cdk_mocks()
    _install_mocks(mocks)
    try:
        IdpStack = _import_stack()
        app = mocks["MockApp"]()
        IdpStack(app, "TestStack")

        outputs = mocks["outputs_created"]
        output_ids = [o["id"] for o in outputs]

        assert len(outputs) >= 3, (
            f"Expected at least 3 CfnOutputs, got {len(outputs)}: {output_ids}"
        )

        # Check for bucket name output
        assert any("BucketName" in oid for oid in output_ids), (
            f"Expected a CfnOutput containing 'BucketName', got {output_ids}"
        )

        # Check for bucket ARN output
        assert any("BucketArn" in oid for oid in output_ids), (
            f"Expected a CfnOutput containing 'BucketArn', got {output_ids}"
        )

        # Check for role name output
        assert any("Role" in oid for oid in output_ids), (
            f"Expected a CfnOutput containing 'Role', got {output_ids}"
        )
    finally:
        _cleanup_mocks()


def test_s3_bucket_lifecycle_rules():
    """Test that S3 bucket has correct lifecycle rules."""
    mocks = _build_cdk_mocks()
    _install_mocks(mocks)
    try:
        IdpStack = _import_stack()
        app = mocks["MockApp"]()
        IdpStack(app, "TestStack")

        buckets = mocks["buckets_created"]
        bucket = next(b for b in buckets if b.bucket_name == "ntkey-idp-documents")
        rules = bucket.props.get("lifecycle_rules", [])

        assert len(rules) >= 2, f"Expected at least 2 lifecycle rules, got {len(rules)}"

        # Check abort incomplete multipart rule
        abort_rule = next(
            (r for r in rules if r.get("id") == "AbortIncompleteMultipart"), None
        )
        assert abort_rule is not None, "Missing AbortIncompleteMultipart lifecycle rule"
        assert abort_rule["abort_incomplete_multipart_upload_after"] == {"days": 7}, (
            "AbortIncompleteMultipart should be 7 days"
        )

        # Check BDA output expiry rule
        bda_rule = next(
            (r for r in rules if r.get("id") == "ExpireBDAOutput"), None
        )
        assert bda_rule is not None, "Missing ExpireBDAOutput lifecycle rule"
        assert bda_rule["prefix"] == "bda-output/", "BDA output prefix should be 'bda-output/'"
        assert bda_rule["expiration"] == {"days": 90}, "BDA output expiration should be 90 days"
    finally:
        _cleanup_mocks()


def test_s3_bucket_cors():
    """Test that S3 bucket has correct CORS configuration."""
    mocks = _build_cdk_mocks()
    _install_mocks(mocks)
    try:
        IdpStack = _import_stack()
        app = mocks["MockApp"]()
        IdpStack(app, "TestStack")

        buckets = mocks["buckets_created"]
        bucket = next(b for b in buckets if b.bucket_name == "ntkey-idp-documents")
        cors_rules = bucket.props.get("cors", [])

        assert len(cors_rules) >= 1, "Expected at least 1 CORS rule"
        cors = cors_rules[0]
        assert "PUT" in cors["allowed_methods"], "CORS should allow PUT"
        assert "POST" in cors["allowed_methods"], "CORS should allow POST"
        assert "GET" in cors["allowed_methods"], "CORS should allow GET"
        assert "*" in cors["allowed_origins"], "CORS should allow all origins"
        assert "*" in cors["allowed_headers"], "CORS should allow all headers"
    finally:
        _cleanup_mocks()
