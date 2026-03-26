import { FormField, Select, SelectProps } from '@cloudscape-design/components';
import { FC, useState } from 'react';
import { ParameterLabel, ParameterProps } from './parameter-types';

type DropdownParameterProps = ParameterProps & {
  onChange?: (value?: string) => void,
  value?: string,
  showDescription?: boolean,
  removeParameterOption?: string,
};

// eslint-disable-next-line complexity
const productParameterDropdown: FC<DropdownParameterProps> = ({
  parameter,
  parameterLabelSubHeading,
  onChange,
  showDescription,
  removeParameterOption,
}) => {
  const [value, setValue] = useState(parameter.defaultValue);

  const mappedOptions = parameter.
    parameterConstraints?.
    allowedValues?.
    map<SelectProps.Option>(v => ({
      label: ((parameter.parameterMetaData?.optionLabels) as { [key: string]: string })?.[v] || v,
      value: v,
      description: ((parameter.parameterMetaData?.optionWarnings) as { [key: string]: string })?.[v] || '',
    })) || [];

  const options = removeParameterOption
    ? mappedOptions.filter(option => option.value !== removeParameterOption)
    : mappedOptions;

  const selectedOption = options.find(o => o.value === value) || null;

  const parameterLabel = parameter.parameterMetaData?.label || parameter.parameterKey;

  // eslint-disable-next-line @typescript-eslint/no-magic-numbers
  return <> {options.length > 0 &&
    <FormField
      label={renderLabel()}
      description={showDescription ? parameter.description : null}
    >
      <Select
        selectedOption={selectedOption}
        onChange={({ detail }) => handleValueChange(detail.selectedOption.value)}
        options={options}
        selectedAriaLabel="Selected"
        data-test={`param-select-${parameter.parameterKey}`}
      />
    </FormField>}
  </>;

  function handleValueChange(value?: string) {
    setValue(value);
    if (onChange) {
      onChange(value);
    }
  }

  function renderLabel() {
    return <>
      <ParameterLabel
        parameterLabel={parameterLabel}
        parameterLabelSubHeading={parameterLabelSubHeading}
      />
    </>;
  }
};

export { productParameterDropdown as ProductParameterDropdown };
