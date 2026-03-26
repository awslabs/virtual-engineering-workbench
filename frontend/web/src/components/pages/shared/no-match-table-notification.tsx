import { Box, Button } from '@cloudscape-design/components';
import { RoleBasedFeature } from '../../../state';
import { RoleAccessToggle } from './role-access-toggle';

function noMatchNotification({
  title,
  subtitle,
  buttonText,
  buttonAction,
  requiredFeature
}: {
  title: string,
  buttonText: string,
  subtitle: string,
  buttonAction: () => void,
  requiredFeature?: RoleBasedFeature,
}): JSX.Element {
  return (
    <Box textAlign="center" color="inherit">
      <b>{title}</b>
      <Box
        padding={{ bottom: 's' }}
        variant="p"
        color="inherit"
      >
        {subtitle}
      </Box>
      { requiredFeature
        ? <RoleAccessToggle feature={requiredFeature}>
          <Button onClick={buttonAction}>
            {buttonText}
          </Button>
        </RoleAccessToggle>
        : <Button onClick={buttonAction}>{buttonText}</Button>
      }
    </Box>
  );
}

export { noMatchNotification as NoMatchTableNotification };
