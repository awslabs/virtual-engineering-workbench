// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { FC } from 'react';
import { BreadcrumbGroup, BreadcrumbGroupProps } from '@cloudscape-design/components';

import './breadcrumb.scss';
import { useNavigate } from 'react-router-dom';

/* eslint @typescript-eslint/no-empty-interface: "off", no-empty-pattern: "off" */

export interface BreadcrumbItem {
  path: string,
  href: string,
}

interface Props {
  items: BreadcrumbItem[],
}

const breadcrumb: FC<Props> = ({
  items
}) => {
  const navigate = useNavigate();

  function buildItems() : BreadcrumbGroupProps.Item[] {
    return items.map((i) => { return { text: i.path, href: i.href }; });
  }

  return (
    <BreadcrumbGroup
      items={buildItems()}
      onFollow={event => {
        event.preventDefault();
        navigate(event.detail.href);
      }}
    />
  );
};

export { breadcrumb as Breadcrumb };
