import { FormField, Spinner, Select, SelectProps } from '@cloudscape-design/components';
import { FC } from 'react';
import { USER_ROLE_MAP } from '../project-details/project-users.static';


interface Params {
  memberRoleLevel: SelectProps.Option,
  setMemberRoleLevel: (val: SelectProps.Option) => void,
  loading?: boolean,
  restrictOptions?: boolean,
}

const i18n = {
  selectFieldLabel: 'Roles',
  selectFieldPlaceholder: 'Select a role',
  Lvl1Label: `Lvl 1 - ${USER_ROLE_MAP.PLATFORM_USER}`,
  Lvl1Description: 'They can use the VEW resources like user profile, workbenches, etc. in PROD stage',
  Lvl2Label: `Lvl 2 - ${USER_ROLE_MAP.BETA_USER}`,
  // eslint-disable-next-line @stylistic/max-len
  Lvl2Description: 'They can do all of the above and also use VEW resources such as user profiles, workbenches, etc. in QA stage.',
  Lvl3Label: `Lvl 3 - ${USER_ROLE_MAP.PRODUCT_CONTRIBUTOR}`,

  Lvl3Description: 'They can use the VEW resources like user profile, workbenches, etc. in DEV and QA stage',
  Lvl4Label: `Lvl 4 - ${USER_ROLE_MAP.POWER_USER}`,
  // eslint-disable-next-line @stylistic/max-len
  Lvl4Description: 'They can do all of the above (except DEV access) and also promote resources from the QA stage to the PROD stage.',
  Lvl5Label: `Lvl 5 - ${USER_ROLE_MAP.PROGRAM_OWNER}`,
  // eslint-disable-next-line @stylistic/max-len
  Lvl5Description: 'They can do all of the above and also approve/decline program enrolment requests and update user roles (Lvl 1 - Lvl 4).',
  Lvl6Label: `Lvl 6 - ${USER_ROLE_MAP.ADMIN}`,
  // eslint-disable-next-line @stylistic/max-len
  Lvl6Description: 'They can do all of the above and in addition, onboard/offboard users to the program, approve/decline program enrolment requests and update user roles (Lvl 1 - Lvl 6).',
};

export const DEFAULT_SELECT_ROLE_OPTION = {
  value: '1',
  label: i18n.Lvl1Label,
  description: i18n.Lvl1Description,
};


const projectUserAssignmentRoles: FC<Params> = ({
  memberRoleLevel,
  setMemberRoleLevel,
  loading,
  restrictOptions,
}) => {

  return renderContent();


  function renderContent() {
    return <FormField label={i18n.selectFieldLabel}>
      {loading && <>
        <Spinner />
      </>}
      {!loading && <>
        <Select
          onChange={({ detail }) => setMemberRoleLevel(detail.selectedOption)}
          placeholder={i18n.selectFieldPlaceholder}
          selectedOption={memberRoleLevel}
          virtualScroll
          data-test="onboard-select"
          options={restrictOptions ?
            [
              {
                value: '1',
                label: i18n.Lvl1Label,
                description: i18n.Lvl1Description,
              },
              {
                value: '2',
                label: i18n.Lvl2Label,
                description: i18n.Lvl2Description,
              },
              {
                value: '3',
                label: i18n.Lvl3Label,
                description: i18n.Lvl3Description,
              },
              {
                value: '4',
                label: i18n.Lvl4Label,
                description: i18n.Lvl4Description,
              },
            ] :
            [
              {
                value: '1',
                label: i18n.Lvl1Label,
                description: i18n.Lvl1Description,
              },
              {
                value: '2',
                label: i18n.Lvl2Label,
                description: i18n.Lvl2Description,
              },
              {
                value: '3',
                label: i18n.Lvl3Label,
                description: i18n.Lvl3Description,
              },
              {
                value: '4',
                label: i18n.Lvl4Label,
                description: i18n.Lvl4Description,
              },
              {
                value: '5',
                label: i18n.Lvl5Label,
                description: i18n.Lvl5Description,
              },
              {
                value: '6',
                label: i18n.Lvl6Label,
                description: i18n.Lvl6Description,
              },
            ]
          }
        />
      </>}
    </FormField>;
  }
};

export { projectUserAssignmentRoles as ProjectUserAssignmentRoles };