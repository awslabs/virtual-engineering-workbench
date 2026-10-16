import React from 'react';
import { render, renderHook, screen } from '@testing-library/react';
import { RecoilRoot, useRecoilValue } from 'recoil';
import { describe, it, expect } from 'vitest';
import { notificationsState, selectedProjectState } from '../../../state';
import { ProvisionedProduct } from '../../../services/API/proserve-wb-provisioning-api';
import { failureText, useWorkbenchFailureNotifications } from './workbench-failure.logic';
import { WorkbenchFailureAlert } from './workbench-failure';

const NO_NOTIFICATIONS: unknown[] = [];

function workbench(overrides: Partial<ProvisionedProduct>): ProvisionedProduct {
  return {
    projectId: 'proj-1',
    provisionedProductId: 'vew-pp-1',
    provisionedProductName: 'pp',
    userId: 'u-1',
    status: 'RUNNING',
    productId: 'prod-1',
    productName: 'GPU workbench',
    versionId: 'vers-1',
    versionName: '1.0.3',
    stage: 'PROD',
    region: 'eu-north-1',
    createDate: '2026-10-08T12:02:13Z',
    ...overrides,
  } as ProvisionedProduct;
}

const capacityLaunch = workbench({
  status: 'PROVISIONING_ERROR',
  statusReason: 'InsufficientCapacityInAllAvailabilityZones',
  failure: { code: 'CAPACITY', operation: 'LAUNCH', instanceType: 'g6.xlarge', gpu: true },
});

describe('failureText', () => {
  it('explains a capacity failure with the instance type and the GPU note', () => {
    const text = failureText(capacityLaunch.failure!, 'vew-pp-1', 'eu-north-1');

    expect(text.header).toBe('AWS has no free capacity for g6.xlarge right now');
    expect(text.content).toContain('can\'t be known in advance');
    expect(text.content).toContain('GPU capacity in eu-north-1 is often tight');
    expect(text.content).toContain('Remove this workbench and launch it again.');
  });

  it('leaves the GPU note out for other instance types', () => {
    const failure = { code: 'CAPACITY', operation: 'START', instanceType: 'm7i.xlarge', gpu: false };
    const text = failureText(failure, 'r');

    expect(text.content).not.toContain('GPU');
    expect(text.content).toContain('couldn\'t be started');
  });

  it('sends quota failures to the program admin', () => {
    const text = failureText({ code: 'QUOTA', operation: 'START', instanceType: 'g6.xlarge' }, 'r');

    expect(text.header).toBe('The program\'s AWS quota for g6 instances is used up');
    expect(text.content).toContain('ask your program admin');
  });

  it.each(['PERMISSIONS', 'TEMPLATE', 'UNKNOWN', 'SOMETHING_NEW'])('gives the reference for %s', (code) => {
    expect(failureText({ code, operation: 'LAUNCH' }, 'vew-pp-1').content).toContain('vew-pp-1');
  });
});

describe('WorkbenchFailureAlert', () => {
  function renderAlert(roles: string[]) {
    return render(
      <RecoilRoot initializeState={({ set }) => set(selectedProjectState, { projectId: 'proj-1', roles })}>
        <WorkbenchFailureAlert provisionedProduct={capacityLaunch} />
      </RecoilRoot>
    );
  }

  it('shows the explanation to the owner, without the raw AWS reason', () => {
    renderAlert(['PLATFORM_USER']);

    expect(screen.getByText('AWS has no free capacity for g6.xlarge right now')).toBeTruthy();
    expect(screen.queryByText('AWS reason (admins)')).toBeNull();
  });

  it('adds the raw AWS reason for admins', () => {
    renderAlert(['PROGRAM_OWNER']);

    expect(screen.getByText('AWS reason (admins)')).toBeTruthy();
  });

  it('renders nothing for a workbench that has not failed', () => {
    const { container } = render(
      <RecoilRoot><WorkbenchFailureAlert provisionedProduct={workbench({})} /></RecoilRoot>
    );

    expect(container.textContent).toBe('');
  });
});

describe('useWorkbenchFailureNotifications', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => <RecoilRoot>{children}</RecoilRoot>;

  function useNotified(products: ProvisionedProduct[]) {
    useWorkbenchFailureNotifications(products);
    return useRecoilValue(notificationsState);
  }

  it('notifies when a launch in progress ends in a failure', () => {
    const { result, rerender } = renderHook(({ products }) => useNotified(products), {
      wrapper,
      initialProps: { products: [workbench({ status: 'PROVISIONING' })] },
    });
    expect(result.current).toEqual(NO_NOTIFICATIONS);

    rerender({ products: [capacityLaunch] });

    expect(result.current.map((n) => n.header)).toEqual([
      'GPU workbench: AWS has no free capacity for g6.xlarge right now',
    ]);
  });

  it('does not notify for a failure that was already there when the page opened', () => {
    const { result, rerender } = renderHook(({ products }) => useNotified(products), {
      wrapper,
      initialProps: { products: [capacityLaunch] },
    });
    rerender({ products: [{ ...capacityLaunch }] });

    expect(result.current).toEqual(NO_NOTIFICATIONS);
  });
});
