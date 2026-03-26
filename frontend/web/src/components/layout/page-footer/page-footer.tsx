import { FC } from 'react';
import './page-footer.scss';
import { useUserProfile } from '../../user-preferences/user-profile.hook';
import { getApis } from '../../../utils/api-helpers';

/* eslint @stylistic/max-len: "off" */
export const PageFooter: FC = () => {
  const { userProfile } = useUserProfile({ serviceAPIs: getApis() });
  const renderApplicationVersion = () => {
    if (!userProfile.applicationVersionBackend || !userProfile.applicationVersionFrontend) {
      return <></>;
    }
    return <span style={{ float: 'right' }}>FE: v{userProfile.applicationVersionFrontend} &nbsp;&nbsp;&nbsp;&nbsp; BE: v{userProfile.applicationVersionBackend}</span>;
  };
  return (
    <footer id='f' className='footer'>
      &nbsp;
      {renderApplicationVersion()}
    </footer>
  );
};
