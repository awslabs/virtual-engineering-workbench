import { useEffect, useMemo, useState } from 'react';
import { useRecoilValue } from 'recoil';
import { filteredProjectsWithAnyRole } from '../../../../../state';
import {
  ComponentShareModalHookProps,
  ComponentShareModalHookResult,
  SelectableOption,
} from './interfaces';

export function useComponentShareModal(
  hookProps: ComponentShareModalHookProps
): ComponentShareModalHookResult {
  const userProjects = useRecoilValue(filteredProjectsWithAnyRole);
  const [isShareListValid, setIsShareListValid] = useState(false);
  const [selectedOptions, setSelectedOptions] = useState<SelectableOption[]>(
    []
  );
  const { selectableOptions, preselectProjects } = useMemo(() => {
    const selectableOptions = userProjects.map((item) => {
      return {
        label: item.name,
        value: item.id,
        description: item.description,
        disabled: hookProps.associatedProjectIds.includes(item.id),
      };
    });

    const preselectProjects = selectableOptions.filter((prj) =>
      hookProps.associatedProjectIds.includes(prj.value)
    );

    return { selectableOptions, preselectProjects };
  }, [userProjects, hookProps.associatedProjectIds]);

  useEffect(() => {
    setSelectedOptions(preselectProjects);
  }, [preselectProjects]);

  useEffect(() => {
    setIsShareListValid(
      !!selectedOptions.filter((op) => !op.disabled).length
    );
  }, [selectedOptions]);

  const projectIdsForShare = useMemo(() => {
    const options = selectedOptions.filter((p) => p.value && !p.disabled);
    return options.map((o) => o.value || '');
  }, [selectedOptions]);

  return {
    ...hookProps,
    ...{
      selectableOptions,
      selectedOptions,
      setSelectedOptions,
      isShareListValid,
      projectIdsForShare,
    },
  };
}
