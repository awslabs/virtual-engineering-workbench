/* eslint max-classes-per-file: "off" */
import { ProductParameterDropdown } from './product-parameter-dropdown';
import { ProductParameterFreetext } from './product-parameter-freetext';
import { ProductParameterReadonly } from './product-parameter-readonly';
import { ProductParameter } from '../../../../services/API/proserve-wb-provisioning-api';
import { ParameterProps } from './parameter-types';

type ParameterRendererProps = ParameterProps & {
  onChange?: (value?: string) => void,
};

export interface ParameterRenderer {
  canHandle: (parameter: ProductParameter) => boolean,
  render: (props: ParameterRendererProps) => JSX.Element | null,
}

const EMPTY_STRING_CHAR_AMOUNT = 0;
export class ReadonlyParameterRenderer implements ParameterRenderer {
  canHandle = (
    parameter: ProductParameter
  ) => {
    return !!parameter.defaultValue && parameter.defaultValue.length > EMPTY_STRING_CHAR_AMOUNT;
  };
  render = (props: ParameterRendererProps) =>
    <ProductParameterReadonly
      parameter={props.parameter}
      key={props.parameter.parameterKey}
      parameterLabelSubHeading={props.parameterLabelSubHeading}
    />;
}

export class DropdownParameterRenderer implements ParameterRenderer {
  canHandle = (
    parameter: ProductParameter
  ) => (parameter.parameterConstraints?.allowedValues ?? []).length > EMPTY_STRING_CHAR_AMOUNT;
  render = (props: ParameterRendererProps) =>
    <ProductParameterDropdown
      parameter={props.parameter}
      onChange={props.onChange}
      key={props.parameter.parameterKey}
      parameterLabelSubHeading={props.parameterLabelSubHeading}
    />;
}


export class FreetextParameterRenderer implements ParameterRenderer {
  canHandle = (
    parameter: ProductParameter
  ) => (parameter.parameterConstraints?.allowedValues ?? '').length === EMPTY_STRING_CHAR_AMOUNT;
  render = (props: ParameterRendererProps) =>
    <ProductParameterFreetext
      parameter={props.parameter}
      onChange={props.onChange}
      key={props.parameter.parameterKey}
      parameterLabelSubHeading={props.parameterLabelSubHeading}
    />;
}
