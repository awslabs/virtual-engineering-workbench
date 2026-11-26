// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ImportImageStepAmi } from './import-image-step-ami';
import { HandoffStatus } from './import-image-wizard.logic';

const renderStep = (handoffStatus: HandoffStatus) => render(
  <ImportImageStepAmi
    imageSource="MARKETPLACE_PRODUCT"
    importableAmis={[]}
    loadingAmis={false}
    selectedAmi={null}
    setSelectedAmi={vi.fn()}
    subscriptions={[]}
    loadingSubscriptions={false}
    selectedSubscription={null}
    handleSubscriptionSelection={vi.fn()}
    handoffStatus={handoffStatus}
  />,
);

const notice = (container: HTMLElement, name: string) =>
  container.querySelector(`[data-test="${name}"]`);

describe('ImportImageStepAmi — purchase hand-off notice', () => {
  it('tells the user to reload when the purchased product is not listed', () => {
    const { container } = renderStep('unavailable');
    const text = notice(container, 'handoff-unavailable')?.textContent;
    expect(text).toContain('can take a few minutes to appear');
    expect(text).toContain('Reload the page');
    expect(notice(container, 'handoff-already-imported')).toBeNull();
  });

  it('says the product is already imported', () => {
    const { container } = renderStep('alreadyImported');
    expect(notice(container, 'handoff-already-imported')?.textContent)
      .toBe('This product is already imported in this project.');
    expect(notice(container, 'handoff-unavailable')).toBeNull();
  });

  it.each<HandoffStatus>(['none', 'pending', 'selected'])('shows no notice when %s', (status) => {
    const { container } = renderStep(status);
    expect(notice(container, 'handoff-unavailable')).toBeNull();
    expect(notice(container, 'handoff-already-imported')).toBeNull();
  });
});
