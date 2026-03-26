import '@cloudscape-design/global-styles/dark-mode-utils.css';
import {
  Box
} from '@cloudscape-design/components';


export const NotFound = () => {

  return <Box textAlign='center'>
    <img
      className="awsui-util-hide-in-dark-mode"
      src="/404.svg"
      alt="404"
    />
    <img
      className="awsui-util-show-in-dark-mode"
      src="/404_dark.svg"
      alt="404-dark"
    />
  </Box>;
};