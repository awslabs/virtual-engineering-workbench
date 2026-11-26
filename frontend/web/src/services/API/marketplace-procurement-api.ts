// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Marketplace procurement client.
//
// Wraps the five procurement operations (purchase options, offer, quote,
// accept, cancel) of the generated packaging client. The request and response
// types are the generated models, re-exported under the names the wizard uses.
import {
  AcceptAgreementRequestResponse,
  CancelAgreementResponse,
  CreateAgreementRequestRequest,
  CreateAgreementRequestResponse,
  GetMarketplaceOfferResponse,
  ListPurchaseOptionsResponse,
  MarketplaceOfferProductAssociationResponseItem,
  MarketplaceOfferTermResponseItem,
  MarketplacePurchaseOptionResponseItem,
} from './proserve-wb-packaging-api';
import { callApi } from './marketplace-api-support';

export type {
  AcceptAgreementRequestResponse,
  CancelAgreementResponse,
  CreateAgreementRequestResponse,
  GetMarketplaceOfferResponse,
  ListPurchaseOptionsResponse,
};
export type MarketplacePurchaseOption = MarketplacePurchaseOptionResponseItem;
export type MarketplaceOfferProductAssociation = MarketplaceOfferProductAssociationResponseItem;
export type MarketplaceOfferTerm = MarketplaceOfferTermResponseItem;
export type CreateAgreementRequestBody = CreateAgreementRequestRequest;

export class ProcurementApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ProcurementApiError';
    this.status = status;
    this.code = code;
  }
}

const makeError = (message: string, status: number, code?: string) =>
  new ProcurementApiError(message, status, code);

export const marketplaceProcurementAPI = {
  listPurchaseOptions: (projectId: string): Promise<ListPurchaseOptionsResponse> =>
    callApi(
      (api, authorization) => api.listMarketplacePurchaseOptions({ authorization, projectId }),
      makeError,
    ),

  getOffer: (projectId: string, offerId: string): Promise<GetMarketplaceOfferResponse> =>
    callApi(
      (api, authorization) => api.getMarketplaceOffer({ authorization, projectId, offerId }),
      makeError,
    ),

  createAgreementRequest: (
    projectId: string,
    offerId: string,
    body: CreateAgreementRequestBody,
  ): Promise<CreateAgreementRequestResponse> =>
    callApi(
      (api, authorization) => api.createMarketplaceQuote({
        authorization,
        projectId,
        offerId,
        createAgreementRequestRequest: { productType: 'AmiProduct', ...body },
      }),
      makeError,
    ),

  // Account-scoped: accepting a quote commits the buyer ACCOUNT to an AWS
  // Marketplace agreement, so there is no project in the path. See the
  // backend handler for why the former projectId segment was removed.
  acceptAgreementRequest: (agreementRequestId: string): Promise<AcceptAgreementRequestResponse> =>
    callApi(
      (api, authorization) => api.acceptMarketplaceQuote({ authorization, agreementRequestId }),
      makeError,
    ),

  // Account-scoped, see `acceptAgreementRequest`.
  cancelAgreement: (agreementId: string): Promise<CancelAgreementResponse> =>
    callApi(
      (api, authorization) => api.cancelMarketplaceAgreement({ authorization, agreementId }),
      makeError,
    ),
};

export type MarketplaceProcurementAPI = typeof marketplaceProcurementAPI;
