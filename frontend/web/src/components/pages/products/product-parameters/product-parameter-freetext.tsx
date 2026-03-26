/* eslint-disable complexity */

import { FormField, Input } from '@cloudscape-design/components';
import { FC, useEffect, useState } from 'react';
import { ParameterLabel, ParameterProps } from './parameter-types';

type FreetextParameterProps = ParameterProps & {
  onChange?: (value?: string) => void,
  value?: string,
};

const i18n = {
  valueErrorText: 'Entered value is not correct',
  regexValueConstraintDescription: (
    pattern: string
  ) => `Value must satisfy a "${pattern}" regular expression constraint.`,
  maxLengthValueConstraintDescription: (
    maxLength: string
  ) => `Value must not be longer than ${maxLength} characters`,
  minLengthValueConstraintDescription: (
    minLength: string
  ) => `Value must be longer than ${minLength} characters`,
  maxValueConstraintDescription: (
    maxValue: string
  ) => `Value must not be higher than ${maxValue}`,
  minValueConstraintDescription: (
    minValue: string
  ) => `Value must not be lower than ${minValue}`,
};

const productParameterFreetext: FC<FreetextParameterProps> = ({
  parameter,
  parameterLabelSubHeading,
  onChange,
}) => {
  const [value, setValue] = useState(parameter.defaultValue || '');
  const [errorText, setErrorText] = useState<string>();
  const [constraintText, setConstraintText] = useState<string>();
  const validators = [
    () => validateRegex(),
    () => validateMaxLength(),
    () => validateMinLength(),
    () => validateMaxValue(),
    () => validateMinValue(),
    () => removeValidation()
  ];

  useEffect(() => {
    if (!value) { return; }

    isValid();
  }, [value]);

  const parameterLabel = parameter.parameterMetaData?.label || parameter.parameterKey;

  return <>
    <FormField
      label={renderLabel()}
      description={parameter.description}
      errorText={errorText}
      constraintText={constraintText}
    >
      <Input
        value={value}
        placeholder=""
        onChange={({ detail: { value } }) => handleValueChange(value)}
        data-test={`param-freetext-${parameter.parameterKey}`}
      />
    </FormField>
  </>;

  function handleValueChange(value: string) {
    setValue(value);
    if (onChange) {
      onChange(value);
    }
  }

  function isValid() {
    return validators.some(v => !v());
  }

  function validateRegex(): boolean {
    if (parameter.parameterConstraints?.allowedPattern) {
      const regex = new RegExp(parameter.parameterConstraints?.allowedPattern ?? '', 'ug');
      if (!regex.test(value)) {
        setErrorText(i18n.valueErrorText);
        setConstraintText(
          i18n.regexValueConstraintDescription(parameter.parameterConstraints?.allowedPattern ?? '')
        );
        return false;
      }
    }
    return true;
  }

  function validateMaxLength(): boolean {
    if (parameter.parameterConstraints?.maxLength) {
      if (value.length > parseInt(parameter.parameterConstraints?.maxLength ?? 'Infinity', 10)) {
        setErrorText(i18n.valueErrorText);
        setConstraintText(
          i18n.maxLengthValueConstraintDescription(
            parameter.parameterConstraints?.maxLength ?? ''
          )
        );
        return false;
      }
    }
    return true;
  }

  function validateMinLength(): boolean {
    if (parameter.parameterConstraints?.minLength) {
      if (value.length < parseInt(parameter.parameterConstraints?.minLength ?? '0', 10)) {
        setErrorText(i18n.valueErrorText);
        setConstraintText(
          i18n.minLengthValueConstraintDescription(
            parameter.parameterConstraints?.minLength ?? ''
          )
        );
        return false;
      }
    }
    return true;
  }

  function validateMaxValue(): boolean {
    if (parameter.parameterConstraints?.maxValue) {
      if (parseFloat(value) > parseFloat(parameter.parameterConstraints?.maxValue ?? 'Infinity')) {
        setErrorText(i18n.valueErrorText);
        setConstraintText(i18n.maxValueConstraintDescription(parameter.parameterConstraints?.maxValue ?? ''));
        return false;
      }
    }
    return true;
  }

  function validateMinValue(): boolean {
    if (parameter.parameterConstraints?.minValue) {
      if (parseFloat(value) > parseFloat(parameter.parameterConstraints?.minValue ?? '0')) {
        setErrorText(i18n.valueErrorText);
        setConstraintText(i18n.minValueConstraintDescription(parameter.parameterConstraints?.minValue ?? ''));
        return false;
      }
    }
    return true;
  }

  function removeValidation(): boolean {
    setErrorText(undefined);
    setConstraintText(undefined);
    return true;
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

export { productParameterFreetext as ProductParameterFreetext };
