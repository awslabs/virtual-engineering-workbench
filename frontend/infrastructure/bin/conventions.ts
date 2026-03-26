// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
export const getStackName =
  (
    componentName: string,
    componentEnvironment: string
  ): string => `${componentName}-${componentEnvironment}`;

export const getResourceName =
  (componentName: string, resourceName: string, environment: string): string => `${componentName}-${resourceName}-${environment}`;
