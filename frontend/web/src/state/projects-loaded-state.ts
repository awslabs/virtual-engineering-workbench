// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { atom } from 'recoil';

export const projectsLoadedState = atom<boolean>({
  key: 'projects-loaded',
  default: false
});
