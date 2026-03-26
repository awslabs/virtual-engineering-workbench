import { Box, Button } from '@cloudscape-design/components';

function noMatchNotification({
  title,
  clearButtonText,
  clearButtonAction
}: {
  title: string,
  clearButtonText: string,
  clearButtonAction: () => void,
}): JSX.Element {
  return (
    <Box textAlign="center" color="inherit">
      <Box><b>{title}</b></Box>
      <Button onClick={clearButtonAction}>{clearButtonText}</Button>
    </Box>
  );
}

export { noMatchNotification as NoMatchGridNotification };
