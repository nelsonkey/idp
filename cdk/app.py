#!/usr/bin/env python3
"""CDK app entry point for IDP infrastructure."""

import os

import aws_cdk as cdk
from stacks.idp_stack import IdpStack

app = cdk.App()

IdpStack(
    app,
    "IdpStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    ),
)

app.synth()
