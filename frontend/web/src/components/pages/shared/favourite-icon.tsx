import { Icon, Link, Spinner } from '@cloudscape-design/components';
import { useState } from 'react';

type Props = {
  favoriteItems: string[],
  itemId: string,
  onClick(): Promise<void>,
};

export function favouriteIcon({ favoriteItems, itemId, onClick }: Props) {

  const [isLoading, setIsLoading] = useState(false);

  return (
    isLoading ?
      <div className='center-icon'><Spinner /></div> :
      <Link onFollow={async () => {
        setIsLoading(true);
        try {
          return await onClick();
        } finally {
          setIsLoading(false);
        }
      }}>
        <Icon name={favoriteItems.includes(itemId) ? 'star-filled' : 'star'}
          size="medium" data-test="favorite-icon"></Icon>
      </Link>
  );
}

export { favouriteIcon as FavouriteIcon };