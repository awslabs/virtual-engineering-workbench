import { useRef, useState } from 'react';
import { useNotifications } from '../../components/layout';
import {
  marketplaceProcurementAPI,
  CreateAgreementRequestBody,
  CreateAgreementRequestResponse,
} from '../../services/API/marketplace-procurement-api';

interface ServiceAPI {
  createAgreementRequest: (
    projectId: string,
    offerId: string,
    body: CreateAgreementRequestBody,
  ) => Promise<CreateAgreementRequestResponse>,
}

const INITIAL_REQUEST_ID = 0;
const REQUEST_ID_STEP = 1;

export const useCreateAgreementRequest = ({
  serviceApi = marketplaceProcurementAPI,
  projectId,
}: { serviceApi?: ServiceAPI, projectId: string }) => {
  const { showErrorNotification } = useNotifications();
  const [data, setData] = useState<CreateAgreementRequestResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Monotonic request id. Incremented on every `run` AND every `reset`, so any
  // response whose id is no longer the current one is a *superseded* response
  // and must not be written to state.
  //
  // Why this is not optional: a quote is a priced commitment. The procurement
  // wizard resets the quote whenever the buyer changes their pricing
  // configuration, but a reset cannot cancel a request already in flight with
  // the old configuration. Without this guard the old request's `setData` lands
  // *after* the reset and the buyer is shown — and can accept — a quote priced
  // for a configuration they already abandoned. A `useRef` (not state) because
  // the comparison must see the value as of the moment the promise settles,
  // not the value captured when `run` was invoked.
  const requestIdRef = useRef(INITIAL_REQUEST_ID);

  const run = async (
    offerId: string,
    body: CreateAgreementRequestBody,
  ): Promise<CreateAgreementRequestResponse | null> => {
    requestIdRef.current += REQUEST_ID_STEP;
    const requestId = requestIdRef.current;
    const isCurrent = () => requestIdRef.current === requestId;

    setIsLoading(true);
    setError(null);
    try {
      const result = await serviceApi.createAgreementRequest(projectId, offerId, body);
      if (!isCurrent()) {
        // Superseded while in flight. Drop the result on the floor: returning it
        // to the caller is fine (the caller awaited *this* call), but it must
        // never become the quote the Accept step reads.
        return null;
      }
      setData(result);
      return result;
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      if (!isCurrent()) {
        // Superseded request failed — surfacing this would show the buyer an
        // error for a configuration they have already moved on from.
        return null;
      }
      setError(err);
      showErrorNotification({
        header: 'Failed to create Marketplace quote',
        content: err.message,
      });
      return null;
    } finally {
      if (isCurrent()) {
        setIsLoading(false);
      }
    }
  };

  const reset = () => {
    // Invalidate any in-flight request so its response cannot land after this
    // point. Also clears `isLoading` — the thing that was loading is now
    // disowned, so leaving the flag set would wedge the wizard's Next button.
    requestIdRef.current += REQUEST_ID_STEP;
    setData(null);
    setError(null);
    setIsLoading(false);
  };

  return { data, isLoading, error, run, reset };
};
