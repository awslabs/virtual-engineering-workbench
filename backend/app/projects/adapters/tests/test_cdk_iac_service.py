import subprocess
from unittest import mock

import assertpy
import pytest

from app.projects.adapters.exceptions import adapter_exception
from app.projects.adapters.services.cdk_iac_service import CDKIACService


@mock.patch("subprocess.run")
def test_deploy_iac_runs_bootstrap_and_deploy(mock_run, mock_logger):
    # ARRANGE
    aws_account_id = "123456789012"
    region = "us-east-1"
    service = CDKIACService(
        toolkit_stack_name="VEWCDKToolkit",
        toolkit_stack_qualifier="ioc760get",
        bootstrap_role="VEWBootstrapRole",
        logger=mock_logger,
    )

    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

    # ACT
    service.deploy_iac(aws_account_id, region, {"key": "value"})

    # ASSERT
    mock_run.assert_any_call(
        [
            "cdk",
            "bootstrap",
            "aws://123456789012/us-east-1",
            "--context",
            "key=value",
            "--qualifier",
            "ioc760get",
            "--toolkit-stack-name",
            "VEWCDKToolkit",
        ],
        shell=False,
        text=True,
        capture_output=True,
        check=True,
        timeout=600,
    )
    mock_run.assert_any_call(
        [
            "cdk",
            "deploy",
            "--context",
            "key=value",
            "--require-approval",
            "never",
            "'*'",
            "--concurrency",
            "10",
        ],
        shell=False,
        text=True,
        capture_output=True,
        check=True,
        timeout=1800,
    )
    assert mock_run.call_count == 2


@mock.patch("subprocess.run")
def test_deploy_iac_when_bootstrap_fails_raises(mock_run, mock_logger):
    # ARRANGE
    aws_account_id = "123456789012"
    region = "us-east-1"
    service = CDKIACService(
        toolkit_stack_name="VEWCDKToolkit",
        toolkit_stack_qualifier="ioc760get",
        bootstrap_role="VEWBootstrapRole",
        logger=mock_logger,
    )

    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=[], stderr="Test error")

    # ACT
    with pytest.raises(adapter_exception.AdapterException) as e:
        service.deploy_iac(aws_account_id, region, {"key": "value"})

    # ASSERT
    assertpy.assert_that(str(e.value)).contains("Bootstrap failed")


@mock.patch("subprocess.run")
def test_deploy_iac_runs_bootstrap_with_lookup_and_deploy(mock_run, mock_logger):
    # ARRANGE
    aws_account_id = "123456789012"
    region = "us-east-1"
    service = CDKIACService(
        toolkit_stack_name="VEWCDKToolkit",
        toolkit_stack_qualifier="ioc760get",
        bootstrap_role="VEWBootstrapRole",
        trusted_account="123456789012",
        enable_lookup=True,
        logger=mock_logger,
    )

    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

    # ACT
    service.deploy_iac(aws_account_id, region, {"key": "value"})

    # ASSERT
    mock_run.assert_any_call(
        [
            "cdk",
            "bootstrap",
            "aws://123456789012/us-east-1",
            "--context",
            "key=value",
            "--qualifier",
            "ioc760get",
            "--toolkit-stack-name",
            "VEWCDKToolkit",
            "--trust",
            "123456789012",
            "--trust-for-lookup",
            "123456789012",
        ],
        shell=False,
        text=True,
        capture_output=True,
        check=True,
        timeout=600,
    )
    mock_run.assert_any_call(
        [
            "cdk",
            "deploy",
            "--context",
            "key=value",
            "--require-approval",
            "never",
            "'*'",
            "--concurrency",
            "10",
        ],
        shell=False,
        text=True,
        capture_output=True,
        check=True,
        timeout=1800,
    )
    assert mock_run.call_count == 2


@mock.patch("subprocess.run")
def test_deploy_iac_when_deploy_fails_raises(mock_run, mock_logger):
    # ARRANGE
    aws_account_id = "123456789012"
    region = "us-east-1"
    service = CDKIACService(
        toolkit_stack_name="VEWCDKToolkit",
        toolkit_stack_qualifier="ioc760get",
        bootstrap_role="VEWBootstrapRole",
        logger=mock_logger,
    )

    mock_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=0),
        subprocess.CalledProcessError(returncode=1, cmd=[], stderr="Test error"),
    ]

    # ACT
    with pytest.raises(adapter_exception.AdapterException) as e:
        service.deploy_iac(aws_account_id, region, {"key": "value"})

    # ASSERT
    assertpy.assert_that(str(e.value)).contains("Deploy failed")
