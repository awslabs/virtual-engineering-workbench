import { useState } from 'react';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { AllPrograms } from './all-programs';
import { MyPrograms } from './my-programs';
import { useProjectsSwitch } from '../../../hooks';
import './programs.scss';

export const Programs = () => {
  const { userProjects } = useProjectsSwitch({ skipFetch: true });
  /* eslint @typescript-eslint/no-magic-numbers: "off" */
  const [selectedTab, setSelectedTab] = useState(userProjects.length >= 1 ? 'my-programs' : 'all-programs');

  return (
    <WorkbenchAppLayout
      breadcrumbItems={[]}
      content={selectedTab === 'all-programs'
        ?
        <AllPrograms
          selectedTab={selectedTab}
          setSelectedTab={setSelectedTab}
        />
        : <MyPrograms
          selectedTab={selectedTab}
          setSelectedTab={setSelectedTab}
        />
      }
      contentType="cards"
      navigationHide
      toolsHide
    />
  );
};
