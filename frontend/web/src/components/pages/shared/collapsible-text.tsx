
import { Box, Link, SpaceBetween, SpaceBetweenProps } from '@cloudscape-design/components';
import { FC, useState } from 'react';

const i18n = {
  labelShowFewer: 'Show fewer',
  labelShowMore: '',
};

interface CollapsibleTextProps {
  items: string[],
  minLength?: number,
  size?: SpaceBetweenProps.Size,
  direction?: SpaceBetweenProps.Direction,
}

/* eslint-disable @typescript-eslint/no-magic-numbers */
export const CollapsibleText: FC<CollapsibleTextProps> = ({
  items, minLength = 1, direction = 'horizontal', size = 'xs'
}) => {
  const [isListExpanded, setIsListExpanded] = useState(false);
  const remainingCount = items.length - minLength;

  if (items.length === 0) {
    return '-';
  }

  if (isListExpanded) {
    return <>
      {
        items.map((item) =>
          <Box key={item}>{item}</Box>
        )
      }
      <Link fontSize="body-s" onFollow={() => setIsListExpanded(false)}>{i18n.labelShowFewer}</Link>
    </>;
  }

  return <>
    <SpaceBetween {...{ direction, size }} >
      {items.slice(0, minLength).map((item) =>
        <Box key={item}>{item}</Box>
      )}
      { items.length - minLength > 0 &&
        <Link fontSize="body-s" onFollow={() => setIsListExpanded(true)} >
          {i18n.labelShowMore} (+{remainingCount})
        </Link>
      }
    </SpaceBetween>
  </>;
};