import { Box, Spinner } from '@cloudscape-design/components';
import { ReactNode } from 'react';

interface InfoBoxProps {
  label: string,
  value: number | string | ReactNode | null,
  loading?: boolean,
  'data-test'?: string, // eslint-disable-line @typescript-eslint/naming-convention
}

// eslint-disable-next-line complexity
const infoBox: React.FC<InfoBoxProps> = ({ label, value, loading, 'data-test': dataTest }) =>
  <div data-test={dataTest}>
    <Box variant="awsui-key-label">{label}</Box>
    {!loading && typeof value === 'number' && <Box
      color="text-status-info"
      fontSize="heading-xl"
      fontWeight="bold"
    >
      <b>{value === null ? 'N/A' : value}</b>
    </Box>}
    {!loading && typeof value !== 'number' && <Box>
      {value === null ? 'N/A' : value}
    </Box>}
    {loading && <Spinner />}
  </div>
  ;

export { infoBox as InfoBox };