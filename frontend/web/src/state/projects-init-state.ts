// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { atom } from 'recoil';

export const projectsInitialisedState = atom<boolean>({
  key: 'projects-initialised',
  default: false
});
