/* eslint @typescript-eslint/naming-convention: "off" */

import { ProjectRoles } from '../../../../state';


export const USER_ROLE_MAP: { [key in ProjectRoles]: string } = {
  ADMIN: 'Frontend Admin',
  POWER_USER: 'Power User',
  PROGRAM_OWNER: 'Program Owner',
  PLATFORM_USER: 'Platform User',
  BETA_USER: 'Beta User',
  PRODUCT_CONTRIBUTOR: 'Product Contributor'
};

export const USER_ROLE_LEVEL_MAP: { [key in ProjectRoles]: string } = {
  ADMIN: '6',
  PROGRAM_OWNER: '5',
  POWER_USER: '4',
  PRODUCT_CONTRIBUTOR: '3',
  BETA_USER: '2',
  PLATFORM_USER: '1',
};

export const USER_ROLE_DESCRIPTION: { [key in ProjectRoles]: string } = {
  ADMIN: 'Frontend Admins can onboard AWS accounts and manage users to a program.',
  POWER_USER: 'Power Users can see and provision workbenches in QA and PROD environments.',
  PROGRAM_OWNER: 'Program Owners can approve and reject user enrolment requests.',
  PLATFORM_USER: 'Platform Users can provision workbenches in PROD environment.',
  BETA_USER: 'Beta Users can see and provision workbenches in QA environment.',
  PRODUCT_CONTRIBUTOR: 'Product contributors can see and provision workbenches in DEV and QA environments.'
};